# CHANGELOG

## 0.6.3

- Add `slots: bool = True` key to metaclass, making resulting dataclasses slot-based by default.
- Add `__ARGSPEC_VALIDATED__` as as runtime field on `ArgSpec` objects, staining objects which were created with `__ARGSPEC_SKIP_VALIDATION__`.

## 0.6.2

- Add `.replace(**kwargs)` to ArgSpec instances.

## 0.6.1

- Add `frozen: bool = True` key to metaclass, making resulting dataclasses immutable by default.

## 0.6.0

- Change `positional` (resp. `option`, `flag`) from returning bespoke `Positional` (resp. `Option`, `Flag`) objects to returning `dataclasses.field(..., metadata={"argspec": metadata_object})`.
- Automatically convert `default=mutable_value` to `default_factory=lambda: mutable_value` to prevent shared mutable references in the case where multiple instances of the class are created.
- Add typing overloads to `positional` and `option` to statically disallow `default=val, default_factory=factory`.
- Improve safety of direct instantiation (e.g., `args = Args(x=1)`) for classes to aim to guarantee that `Args(...)` is also valid.
  - Values are automatically passed through the same type coercer.
  - Default values/factories are applied to any unspecified values, where possible.
  - If any fields are still unspecified, an error is raised.

## 0.5.0

- Add `converter: (str) -> T` field to `positional` and `option`, allowing for more nuanced conversions, such as `json.loads`.
- Add `secret: bool` parameter to `readenv`, allowing envvars to be suppressed in the help text.
- Add `long: bool` parameter to `option` and `flag`, allowing the suppression of internal names.

## 0.4.1

- Improve README clarity, providing additional context with regard to `pydantic-settings`.
- Improve help/usage message by providing cleaner type hint labels (via update of `typewire` to v1.3.0).

## v0.4.0

- Improve usage rendering of the help flags.
- Add `default_factory` parameter to `positional` and `option`. It is an ArgumentSpecError to provide both `default` and `default_factory`.
- Add `readenv` as a top-level callable meant to be passed as `default_factory=readenv(...)` for providing envvar fallback for keys.
- Provide additional automatic type casting for default values.
- Allow non-argspec objects to be used as values within the class definition. These are ignored by the argspec parser entirely and are thus used in accordance with usual dataclasses behaviour. For example:

```python
class Args(ArgSpec):
    value: int = positional()
    some_list: list[int] = dataclasses.field(default_factory=list)
    bare_value: float = 10.0

args = Args.from_argv(["12"])  # Args(value=12, some_list=[], bare_value=12.0)
```

## v0.3.1

- Correct behaviour of `x: str | None = option(None)` when falling back to default. This now correctly returns `None`, rather than `"None"`.

## v0.3.0

- Add support for `--key=value` (and `-k=value`) syntax for option arguments. Note that this does not allow flags to take arguments: `--verbose=true` is an ArgumentError.

## v0.2.0

- Fixed help messages to include automatic short aliases (which had worked but weren't documented)
- Only provide default `--no-X` flag negators for `default=True` flags when no other negator was provided

## v0.1.0

- Initial release
