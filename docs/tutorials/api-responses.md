**Target page:** [https://slensky.com/zendriver-examples/api-request.html](https://slensky.com/zendriver-examples/api-request.html)

In this tutorial, we will demonstrate how to read a dynamically loaded API response using response expectations.

The example page simulates an API request by waiting for a few seconds and then fetching a static JSON file. While it would be far easier in this case to just fetch the JSON file directly, for demonstration purposes, let's instead pretend that the response comes from a more complex API that cannot easily be called directly.

## Initial setup

Begin by creating a new script for the tutorial:

```python
--8<-- "docs/tutorials/tutorial-code/api-responses-1.py"
```

## Reading the API response

```python
--8<-- "docs/tutorials/tutorial-code/api-responses-2.py"
```
