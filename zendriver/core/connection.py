from __future__ import annotations

import asyncio
import collections
import inspect
import itertools
import json
import logging
import sys
import types
import typing
from asyncio import iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generator,
    Optional,
    TypeVar,
    Union,
)

import websockets
import websockets.asyncio.client

from .. import cdp
from . import util

if TYPE_CHECKING:
    from zendriver.core.browser import Browser


T = TypeVar("T")

GLOBAL_DELAY = 0.005
MAX_SIZE: int = 2**28
PING_TIMEOUT: int = 900  # 15 minutes

TargetType = Union[cdp.target.TargetInfo, cdp.target.TargetID]

logger = logging.getLogger("uc.connection")


class ProtocolException(Exception):
    def __init__(self, *args, **kwargs):  # real signature unknown
        self.message = None
        self.code = None
        self.args = args
        if isinstance(args[0], dict):
            self.message = args[0].get("message", None)  # noqa
            self.code = args[0].get("code", None)

        elif hasattr(args[0], "to_json"):

            def serialize(obj, _d=0):
                res = "\n"
                for k, v in obj.items():
                    space = "\t" * _d
                    if isinstance(v, dict):
                        res += f"{space}{k}: {serialize(v, _d + 1)}\n"
                    else:
                        res += f"{space}{k}: {v}\n"

                return res

            self.message = serialize(args[0].to_json())

        else:
            self.message = "| ".join(str(x) for x in args)

    def __str__(self):
        return f"{self.message} [code: {self.code}]" if self.code else f"{self.message}"


class SettingClassVarNotAllowedException(PermissionError):
    pass


class Transaction(asyncio.Future):
    def __init__(self, cdp_obj: Generator[dict[str, Any], dict[str, Any], Any]):
        """
        :param cdp_obj:
        """
        super().__init__()
        self.__cdp_obj__ = cdp_obj
        self.connection: Connection | None = None
        self.id: int | None = None

        self.method, *params = next(self.__cdp_obj__).values()
        if params:
            params = params.pop()
        self.params = params

    @property
    def message(self):
        return json.dumps({"method": self.method, "params": self.params, "id": self.id})

    @property
    def has_exception(self):
        try:
            if self.exception():
                return True
        except:  # noqa
            return True
        return False

    def __call__(self, **response: dict):
        """
        parsed the response message and marks the future
        complete

        :param response:
        :return:
        """

        if "error" in response:
            # set exception and bail out
            return self.set_exception(ProtocolException(response["error"]))
        try:
            # try to parse the result according to the py cdp docs.
            self.__cdp_obj__.send(response["result"])
        except StopIteration as e:
            # exception value holds the parsed response
            return self.set_result(e.value)
        raise ProtocolException("could not parse the cdp response:\n%s" % response)

    def __repr__(self):
        success = False if (self.done() and self.has_exception) else True
        if self.done():
            status = "finished"
        else:
            status = "pending"
        fmt = (
            f"<{self.__class__.__name__}\n\t"
            f"method: {self.method}\n\t"
            f"status: {status}\n\t"
            f"success: {success}>"
        )
        return fmt


class EventTransaction(Transaction):
    event = None
    value = None

    def __init__(self, event_object):
        try:
            super().__init__(None)  # type: ignore
        except Exception:
            pass
        self.set_result(event_object)
        self.event = self.value = self.result()

    def __repr__(self):
        status = "finished"
        success = False if self.exception() else True
        event_object = self.result()
        fmt = (
            f"{self.__class__.__name__}\n\t"
            f"event: {event_object.__class__.__module__}.{event_object.__class__.__name__}\n\t"
            f"status: {status}\n\t"
            f"success: {success}>"
        )
        return fmt


class CantTouchThis(type):
    def __setattr__(cls, attr, value):
        """
        :meta private:
        """
        if attr == "__annotations__":
            # fix autodoc
            return super().__setattr__(attr, value)
        raise SettingClassVarNotAllowedException(
            "\n".join(
                (
                    "don't set '%s' on the %s class directly, as those are shared with other objects.",
                    "use `my_object.%s = %s`  instead",
                )
            )
            % (attr, cls.__name__, attr, value)
        )


class Connection(metaclass=CantTouchThis):
    attached: bool
    websocket: websockets.asyncio.client.ClientConnection | None = None
    _target: cdp.target.TargetInfo | None
    _current_id_mutex: asyncio.Lock = asyncio.Lock()

    def __init__(
        self,
        websocket_url: str,
        target: cdp.target.TargetInfo | None = None,
        _owner: Browser | None = None,
        **kwargs,
    ):
        super().__init__()
        self._target = target
        self.__count__ = itertools.count(0)
        self._owner = _owner
        self.websocket_url: str = websocket_url
        self.websocket = None
        self.mapper: dict[int, Transaction] = {}
        self.handlers: dict[Any, list[Union[Callable, Awaitable]]] = (
            collections.defaultdict(list)
        )
        self.recv_task = None
        self.enabled_domains: list[Any] = []
        self._last_result: list[Any] = []
        self.listener: Listener | None = None
        self.__dict__.update(**kwargs)

    @property
    def target(self) -> cdp.target.TargetInfo | None:
        return self._target

    @target.setter
    def target(self, target: cdp.target.TargetInfo):
        if not isinstance(target, cdp.target.TargetInfo):
            raise TypeError(
                "target must be set to a '%s' but got '%s"
                % (cdp.target.TargetInfo.__name__, type(target).__name__)
            )
        self._target = target

    @property
    def closed(self):
        return self.websocket is None

    def add_handler(
        self,
        event_type_or_domain: Union[type, types.ModuleType],
        handler: Union[Callable, Awaitable],
    ):
        """
        add a handler for given event

        if event_type_or_domain is a module instead of a type, it will find all available events and add
        the handler.

        if you want to receive event updates (network traffic are also 'events') you can add handlers for those events.
        handlers can be regular callback functions or async coroutine functions (and also just lamba's).
        for example, you want to check the network traffic:

        .. code-block::

            page.add_handler(cdp.network.RequestWillBeSent, lambda event: print('network event => %s' % event.request))

        the next time you make network traffic you will see your console print like crazy.

        :param event_type_or_domain:
        :type event_type_or_domain:
        :param handler:
        :type handler:

        :return:
        :rtype:
        """
        if isinstance(event_type_or_domain, types.ModuleType):
            for name, obj in inspect.getmembers_static(event_type_or_domain):
                if name.isupper():
                    continue
                if not name[0].isupper():
                    continue
                if type(obj) is type:
                    continue
                if inspect.isbuiltin(obj):
                    continue
                self.handlers[obj].append(handler)

        else:
            self.handlers[event_type_or_domain].append(handler)

    def remove_handlers(
        self,
        event_type: Optional[type] = None,
        handler: Optional[Union[Callable, Awaitable]] = None,
    ):
        """
        remove handlers for given event

        if no event is provided, all handlers will be removed.
        if no handler is provided, all handlers for the event will be removed.

        .. code-block::

                # remove all handlers for all events
                page.remove_handlers()

                # remove all handlers for a specific event
                page.remove_handlers(cdp.network.RequestWillBeSent)

                # remove a specific handler for a specific event
                page.remove_handlers(cdp.network.RequestWillBeSent, handler)
        """

        if handler and not event_type:
            raise ValueError(
                "if handler is provided, event_type should be provided as well"
            )

        if not event_type:
            self.handlers.clear()
            return

        if not handler:
            del self.handlers[event_type]
            return

        if handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)

    async def aopen(self, **kw):
        """
        opens the websocket connection. should not be called manually by users
        :param kw:
        :return:
        """

        if self.websocket is None:
            try:
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_timeout=PING_TIMEOUT,
                    max_size=MAX_SIZE,
                )
                self.listener = Listener(self)
            except (Exception,) as e:
                logger.debug("exception during opening of websocket : %s", e)
                if self.listener:
                    self.listener.cancel()
                raise
        if not self.listener or not self.listener.running:
            self.listener = Listener(self)
            logger.debug("\n✅  opened websocket connection to %s", self.websocket_url)

        # when a websocket connection is closed (either by error or on purpose)
        # and reconnected, the registered event listeners (if any), should be
        # registered again, so the browser sends those events
        await self._register_handlers()

    async def aclose(self):
        """
        closes the websocket connection. should not be called manually by users.
        """
        if self.websocket is not None:
            if self.listener and self.listener.running:
                self.listener.cancel()
                self.enabled_domains.clear()
            await self.websocket.close()
            self.websocket = None
            logger.debug("\n❌ closed websocket connection to %s", self.websocket_url)

    async def sleep(self, t: Union[int, float] = 0.25):
        await self.update_target()
        await asyncio.sleep(t)

    def feed_cdp(self, cdp_obj):
        """
        used in specific cases, mostly during cdp.fetch.RequestPaused events,
        in which the browser literally blocks. using feed_cdp you can issue
        a response without a blocking "await".

        note: this method won't cause a response.
        note: this is not an async method, just a regular method!

        :param cdp_obj:
        :type cdp_obj:
        :return:
        :rtype:
        """
        asyncio.ensure_future(self.send(cdp_obj))

    async def wait(self, t: int | float | None = None):
        """
        waits until the event listener reports idle (no new events received in certain timespan).
        when `t` is provided, ensures waiting for `t` seconds, no matter what.

        :param t:
        :type t:
        :return:
        :rtype:
        """
        if not self.listener:
            raise ValueError("No listener created yet")

        await self.update_target()
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        try:
            if isinstance(t, (int, float)):
                await asyncio.wait_for(self.listener.idle.wait(), timeout=t)
                while (loop.time() - start_time) < t:
                    await asyncio.sleep(0.1)
            else:
                await self.listener.idle.wait()
        except asyncio.TimeoutError:
            if isinstance(t, (int, float)):
                # explicit time is given, which is now passed
                # so bail out early
                return
        except AttributeError:
            # no listener created yet
            pass

    def __getattr__(self, item):
        """:meta private:"""
        try:
            return getattr(self.target, item)
        except AttributeError:
            raise

    async def __aenter__(self):
        """:meta private:"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """:meta private:"""
        await self.aclose()
        if exc_type and exc_val:
            raise exc_type(exc_val)

    def __await__(self):
        """
        updates targets and wait for event listener to report idle.
        idle is reported when no new events are received for the duration of 1 second
        :return:
        :rtype:
        """
        return self.wait().__await__()

    async def update_target(self):
        target_info: cdp.target.TargetInfo = await self.send(
            cdp.target.get_target_info(self.target_id), _is_update=True
        )
        self.target = target_info

    async def send(
        self, cdp_obj: Generator[dict[str, Any], dict[str, Any], T], _is_update=False
    ) -> T:
        """
        send a protocol command. the commands are made using any of the cdp.<domain>.<method>()'s
        and is used to send custom cdp commands as well.

        :param cdp_obj: the generator object created by a cdp method

        :param _is_update: internal flag
            prevents infinite loop by skipping the registeration of handlers
            when multiple calls to connection.send() are made
        :return:
        """
        await self.aopen()
        if self.websocket is None:
            return  # type: ignore
        if self._owner:
            browser = self._owner
            if browser.config:
                if browser.config.expert:
                    await self._prepare_expert()
                if browser.config.headless:
                    await self._prepare_headless()
        if not self.listener or not self.listener.running:
            self.listener = Listener(self)

        tx = Transaction(cdp_obj)
        tx.connection = self
        if not self.mapper:
            self.__count__ = itertools.count(0)
        async with self._current_id_mutex:
            tx.id = next(self.__count__)
        self.mapper.update({tx.id: tx})
        if not _is_update:
            await self._register_handlers()
        await self.websocket.send(tx.message)
        try:
            return await tx
        except ProtocolException as e:
            e.message = e.message or ""
            e.message += f"\ncommand:{tx.method}\nparams:{tx.params}"
            raise e

    #
    async def _register_handlers(self):
        """
        ensure that for current (event) handlers, the corresponding
        domain is enabled in the protocol.

        """
        # save a copy of current enabled domains in a variable
        # domains will be removed from this variable
        # if it is still needed according to the set handlers
        # so at the end this variable will hold the domains that
        # are not represented by handlers, and can be removed
        enabled_domains = self.enabled_domains.copy()
        for event_type in self.handlers.copy():
            if len(self.handlers[event_type]) == 0:
                self.handlers.pop(event_type)
                continue
            if not isinstance(event_type, type):
                continue
            domain_mod = util.cdp_get_module(event_type.__module__)
            if domain_mod in self.enabled_domains:
                # at this point, the domain is being used by a handler
                # so remove that domain from temp variable 'enabled_domains' if present
                if domain_mod in enabled_domains:
                    enabled_domains.remove(domain_mod)
                continue
            elif domain_mod not in self.enabled_domains:
                if domain_mod in (cdp.target, cdp.storage):
                    # by default enabled
                    continue
                try:
                    # we add this before sending the request, because it will
                    # loop indefinite
                    logger.debug("registered %s", domain_mod)
                    self.enabled_domains.append(domain_mod)

                    await self.send(domain_mod.enable(), _is_update=True)

                except:  # noqa - as broad as possible, we don't want an error before the "actual" request is sent
                    logger.debug("", exc_info=True)
                    try:
                        self.enabled_domains.remove(domain_mod)
                    except:  # noqa
                        logger.debug("NOT GOOD", exc_info=True)
                        continue
                finally:
                    continue
        for ed in enabled_domains:
            # we started with a copy of self.enabled_domains and removed a domain from this
            # temp variable when we registered it or saw handlers for it.
            # items still present at this point are unused and need removal
            self.enabled_domains.remove(ed)

    async def _prepare_headless(self):
        if getattr(self, "_prep_headless_done", None):
            return
        response = await self._send_oneshot(
            cdp.runtime.evaluate(
                expression="navigator.userAgent",
                user_gesture=True,
                await_promise=True,
                return_by_value=True,
                allow_unsafe_eval_blocked_by_csp=True,
            )
        )
        if response and response[0].value:
            ua = response[0].value
            await self._send_oneshot(
                cdp.network.set_user_agent_override(
                    user_agent=ua.replace("Headless", ""),
                )
            )
        setattr(self, "_prep_headless_done", True)

    async def _prepare_expert(self):
        if getattr(self, "_prep_expert_done", None):
            return
        if self._owner:
            await self._send_oneshot(
                cdp.page.add_script_to_evaluate_on_new_document(
                    """
                    Element.prototype._attachShadow = Element.prototype.attachShadow;
                    Element.prototype.attachShadow = function () {
                        return this._attachShadow( { mode: "open" } );
                    };
                """
                )
            )

            await self._send_oneshot(cdp.page.enable())
        setattr(self, "_prep_expert_done", True)

    async def _send_oneshot(self, cdp_obj):
        if self.websocket is None:
            raise ValueError("no websocket connection")

        tx = Transaction(cdp_obj)
        tx.connection = self
        tx.id = -2
        self.mapper.update({tx.id: tx})
        await self.websocket.send(tx.message)
        try:
            # in try except since if browser connection sends this it reises an exception
            return await tx
        except ProtocolException:
            pass


class Listener:
    def __init__(self, connection: Connection):
        self.connection = connection
        self.history: collections.deque = collections.deque()
        self.max_history = 1000
        self.task: asyncio.Future | None = None

        # when in interactive mode, the loop is paused after each return
        # and when the next call is made, it might still have to process some events
        # from the previous call as well.

        # while in "production" the loop keeps running constantly
        # (and so events are continuous processed)

        # therefore we should give it some breathing room in interactive mode
        # and we can tighten that room when in production.

        # /example/demo.py runs ~ 5 seconds faster, which is quite a lot.

        is_interactive = getattr(sys, "ps1", sys.flags.interactive)
        self._time_before_considered_idle = 0.10 if not is_interactive else 0.75
        self.idle = asyncio.Event()
        self.run()

    def run(self):
        self.task = asyncio.create_task(self.listener_loop())

    @property
    def time_before_considered_idle(self):
        return self._time_before_considered_idle

    @time_before_considered_idle.setter
    def time_before_considered_idle(self, seconds: Union[int, float]):
        self._time_before_considered_idle = seconds

    def cancel(self):
        if self.task and not self.task.cancelled():
            self.task.cancel()

    @property
    def running(self):
        if not self.task:
            return False
        if self.task.done():
            return False
        return True

    async def listener_loop(self):
        while True:
            if self.connection.websocket is None:
                raise ValueError("no websocket connection")

            try:
                msg = await asyncio.wait_for(
                    self.connection.websocket.recv(), self.time_before_considered_idle
                )
            except asyncio.TimeoutError:
                self.idle.set()
                # breathe
                # await asyncio.sleep(self.time_before_considered_idle / 10)
                continue
            except asyncio.CancelledError:
                logger.debug(
                    "task was cancelled while reading websocket, breaking loop"
                )
                break
            except websockets.exceptions.ConnectionClosedError as e:
                # break on connection closed
                logger.debug(
                    "connection listener exception while reading websocket:\n%s", e
                )
                break

            if not self.running:
                # if we have been cancelled or otherwise stopped running
                # break this loop
                break

            # since we are at this point, we are not "idle" anymore.
            self.idle.clear()

            message = json.loads(msg)
            if "id" in message:
                # response to our command
                if message["id"] in self.connection.mapper:
                    # get the corresponding Transaction

                    # thanks to zxsleebu for discovering the memory leak
                    # pop to prevent memory leaks
                    tx = self.connection.mapper.pop(message["id"])
                    logger.debug("got answer for %s (message_id:%d)", tx, message["id"])

                    # complete the transaction, which is a Future object
                    # and thus will return to anyone awaiting it.
                    tx(**message)
                else:
                    if message["id"] == -2:
                        maybe_tx = self.connection.mapper.get(-2)
                        if maybe_tx:
                            tx = maybe_tx
                            tx(**message)
                        continue
            else:
                # probably an event
                try:
                    event = cdp.util.parse_json_event(message)
                    event_tx = EventTransaction(event)
                    if not self.connection.mapper:
                        self.connection.__count__ = itertools.count(0)
                    event_tx.id = next(self.connection.__count__)
                    self.connection.mapper[event_tx.id] = event_tx
                except Exception as e:
                    logger.info(
                        "%s: %s  during parsing of json from event : %s"
                        % (type(e).__name__, e.args, message),
                        exc_info=True,
                    )
                    continue
                except KeyError as e:
                    logger.info("some lousy KeyError %s" % e, exc_info=True)
                    continue
                try:
                    if type(event) in self.connection.handlers:
                        callbacks = self.connection.handlers[type(event)]
                    else:
                        continue
                    if not len(callbacks):
                        continue
                    for callback in callbacks:
                        try:
                            if iscoroutinefunction(callback):
                                try:
                                    asyncio.create_task(
                                        callback(event, self.connection)
                                    )
                                except TypeError:
                                    asyncio.create_task(callback(event))
                            else:
                                callback = typing.cast(Callable, callback)

                                def run_callback():
                                    try:
                                        callback(event, self.connection)
                                    except TypeError:
                                        callback(event)

                                asyncio.create_task(asyncio.to_thread(run_callback))
                        except Exception as e:
                            logger.warning(
                                "exception in callback %s for event %s => %s",
                                callback,
                                event.__class__.__name__,
                                e,
                                exc_info=True,
                            )
                            raise
                except asyncio.CancelledError:
                    break
                except Exception:
                    raise
                continue

    def __repr__(self):
        s_idle = "[idle]" if self.idle.is_set() else "[busy]"
        s_cache_length = f"[cache size: {len(self.history)}]"
        s_running = f"[running: {self.running}]"
        s = f"{self.__class__.__name__} {s_running} {s_idle} {s_cache_length}>"
        return s
