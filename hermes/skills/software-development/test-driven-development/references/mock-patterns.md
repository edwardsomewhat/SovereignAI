# Python unittest.mock patterns for multi-call scenarios

## side_effect with separate MagicMock for the callable

When mocking a method that gets called multiple times with different return
values, avoid setting `side_effect` directly on `mock.attr` (the dotted form
creates a child MagicMock whose behavior can be unpredictable when the iterable
exhausts). Instead, create an explicit `MagicMock` for the callable:

```python
# WRONG — mock.run.side_effect creates implicit MagicMock, exhausts badly
mock_runner = MagicMock()
mock_runner.run.side_effect = [pkt1, pkt2]

# RIGHT — explicit MagicMock with iter side_effect
mock_runner = MagicMock()
responses = iter([pkt1, pkt2])
mock_runner.run = MagicMock(side_effect=responses)
```

## @patch target resolution

`@patch` resolves the target at decoration time. The target MUST exist as an
attribute on the module. If the function is imported at call time (e.g., inside
a method body), patch where it's DEFINED, not where it's called:

```python
# WRONG — get_runner is imported inside the method, not at module level
@patch("mypackage.module.get_runner")

# RIGHT — patch where the function lives
@patch("mypackage.runners.base.get_runner")
```

When in doubt, use the fully qualified path of the module where the function is
defined (not where it's imported).
