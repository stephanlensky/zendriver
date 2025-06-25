**Target page:** [https://slensky.com/zendriver-examples/login-page.html](https://slensky.com/zendriver-examples/login-page.html)

In this tutorial, we will demonstrate how to fill out a new account sign-up form and then log in with the newly created account. The example page login/signup is implemented entirely with JavaScript, so created accounts do not persist once the tab has been closed.

Feel free to open the page now in your current browser to get an idea of what we will be working with!

## Initial setup

Begin by creating a new script for the tutorial:

```python
--8<-- "docs/tutorials/tutorial-code/account-creation-1.py"
```

## Creating a new account

In this example page, you can create a new account by clicking on the "Sign up" link, which makes the sign-up form visible when clicked.

We can create a new function to click this link, fill out the form, and submit it:

```python
--8<-- "docs/tutorials/tutorial-code/account-creation-2.py:7:30"
```

## Logging in

Next, filling out the login form and logging in:

```python
--8<-- "docs/tutorials/tutorial-code/account-creation-2.py:33:52"
```

## Putting it all together

```python
--8<-- "docs/tutorials/tutorial-code/account-creation-2.py"
```
