**Target page:** [https://cdpdriver.github.io/examples/console.html](https://cdpdriver.github.io/examples/console.html)

In this tutorial, we will explore how to use the Chrome DevTools Protocol (CDP) directly, when Zendriver does not provide
a specific API for the functionality you need.

## Sending CDP commands

To start using CDP, we first need to create a new script for the tutorial. In this example, we will send a command to enable the runtime domain.

```python
--8<-- "docs/tutorials/tutorial-code/cdp-1.py"
```

## Listening to CDP events

Now, let's listen to some CDP events. In this example, we will listen to console messages and print them out.

```python
--8<-- "docs/tutorials/tutorial-code/cdp-2.py"
```
