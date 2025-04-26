**Target page:** [https://slensky.com/zendriver-examples/scrollable-cards.html](https://slensky.com/zendriver-examples/scrollable-cards.html)

In this tutorial, we will demonstrate how to scrape a page with an infinitely scrolling feed. Before we get started, check out the live website to get an idea of what we will be working with!

## Initial setup

Begin by creating a new script for the tutorial:

```python
--8<-- "docs/tutorials/tutorial-code/infinite-scrolling-1.py"
```

In this first version of the code, we do not wait for the cards to load before trying to print them out, so the printed list will always be empty.

## Waiting for cards to appear

To solve this, we need to wait for the cards to load before printing them:

```python
--8<-- "docs/tutorials/tutorial-code/infinite-scrolling-2.py"
```

The above change was a step in the right direction, but what if we want to keep scrolling down until we find the lucky card?

## Finding the lucky card

In this final version of the script, we continuously scroll down to the bottom of the page, waiting for new sets of cards to appear until we find the lucky card.

```python
--8<-- "docs/tutorials/tutorial-code/infinite-scrolling-3.py"
```
