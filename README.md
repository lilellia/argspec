# argspec

A library for cleanly and succinctly performing type-safe command-line argument parsing via a declarative interface.

## Why `argspec`?

I view argument parsing as "the bit that happens before I can actually run my code". It's not part of my problem solving. It's literally just boilerplate to get information into my program so that my program can do its thing. As a result, I want it to be as minimal and as painless as possible. `argspec` aims to make it as invisible as possible without being magic.

```py
from argspec import ArgSpec, positional, option, flag, readenv
import json
from pathlib import Path

class Args(ArgSpec):
    path: Path = positional(help="the path to read")
    api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key to use for the service")
    limit: int = option(10, aliases=["-L"], help="the max number of tries to try doing the thing")
    metadata: dict[str, str] = option(default_factory=dict, converter=json.loads, help="metadata for the messages, given as a JSON string")
    verbose: bool = flag(short=True, help="enable verbose logging")
    send_notifications: bool = flag(aliases=["-n", "--notif"], help="send all notifications")

args = Args.from_argv()  # <-- .from_argv uses sys.argv[1:] by default, but you can provide a list manually if you want
print(args)  # <-- an object with full type inference and autocomplete
```

Of course, you also get a help message (accessible manually by `Args.__argspec_schema__.help()`, but automatically printed with `-h/--help` or on SystemExit from an ArgumentError):

```text
$ python main.py --help

Usage:
     [OPTIONS] PATH

Options:
    -h, --help
    Print this message and exit

    true: -v, --verbose
    enable verbose logging (default: False)

    true: -n, --notif, --send-notifications
    send all notifications (default: False)

    --api-key API_KEY <str>
    the API key to use for the service (default: $SERVICE_API_KEY (currently: 'token=demo-api-key'))

    -L, --limit LIMIT <int>
    the max number of tries to try doing the thing (default: 10)

    --metadata <dict[str, str]>
    metadata for the messages, given as a JSON string (default: {})


Arguments:
    PATH <Path>
    the path to read
```

`ArgSpec` (the class) is built on top of `dataclasses`, so you also get all of the dataclass functions (`__init__`, `__repr__`, etc.) for free:

```py
print(args)  # Args(path=Path('/path/to/file'), api_key='demo-api-key', limit=10, metadata={}, verbose=False, send_notifications=False)
```

### Why not `argparse`?

`argparse` belongs to the standard library and is sufficient for most situations, but while it's capable, it's verbose through it's imperative style and does not allow for type inference and autocomplete.

```py
from argparse import ArgumentParser
import json
import os
from pathlib import Path

parser = ArgumentParser()
parser.add_argument("path", type=Path, help="the path to read")
parser.add_argument("--api-key", default=os.environ["SERVICE_API_KEY"], help="the service API to use (default: $SERVICE_API_KEY)")  # fails at definition time if $SERVICE_API_KEY is not defined
parser.add_argument("-L", "--limit", type=int, default=10, help="the max number of times to try doing the thing (default: 10)")
parser.add_argument("--metadata", default={}, type=json.loads, help="metadata for the messages, given as a JSON string (default: {})")  # no default factory
parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging (default: False)")
parser.add_argument("-n", "--notif", "--send-notifications", action="store_true", help="send all notifications (default: False)")

args = parser.parse_args()
print(args.notifications)  # <-- AttributeError, but you don't get any help from your IDE
```

If you want type safety, you can do something like this:

```py
from argparse import ArgumentParser
from dataclasses import dataclass
import json
import os
from typing import Self

@dataclass
class Args:
    path: Path
    api_key: str
    limit: int
    metadata: dict[str, str]
    verbose: bool
    send_notifications: bool


    @classmethod
    def from_argv(cls) -> Self:
        parser = ArgumentParser()
        parser.add_argument("path", type=Path, help="the path to read")
        parser.add_argument("--api-key", default=os.environ["SERVICE_API_KEY"], help="the service API to use (default: $SERVICE_API_KEY)")  # now fails at instantiation time if $SERVICE_API_KEY is not defined
        parser.add_argument("-L", "--limit", type=int, default=10, help="the max number of times to try doing the thing")
        parser.add_argument("--metadata", default={}, type=json.loads, help="metadata for the messages, given as a JSON string (default: {})")
        parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")
        parser.add_argument("-n", "--notif", "--send-notifications", action="store_true", help="send all notifications")

        return cls(**vars(parser.parse_args()))

args = Args.from_argv()
print(args.send_notifications)  # <-- You do get autocomplete for this
```

But, obviously, that's a pain, and you now have to define your arguments twice, which is a recipe for forgetting to update it in one of those places.

### Why not `cappa`? `typer`/`cyclopts`? `pydantic-settings`?

<details>
<summary>
<a href="https://pypi.org/project/cappa/"><code>cappa</code></a> is very similar, but it relies on <code>typing.Annotated</code> for all of its annotations and also requires you to manually define it as a dataclass.
</summary>

```py
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Annotated
import cappa

@dataclass
class Args:
    path: Annotated[Path, cappa.Arg(help="the path to read")]
    api_key: Annotated[str, cappa.Arg(long=True, help="the API key to use for the service")] = os.environ["SERVICE_API_KEY"]
    limit: Annotated[int, cappa.Arg(short="-L", long=True, help="the max number of times to try doing the thing")] = 10
    metadata: Annotated[dict[str, str], cappa.Arg(parse=json.loads, long=True, help="metadata for the messages, given as a JSON string")] = field(default_factory=dict)
    verbose: Annotated[bool, cappa.Arg(short=True, long=True, help="enable verbose logging")] = False
    send_notifications: Annotated[bool, cappa.Arg(short="-n", long="--notif/--send-notifications", help="send all notifications")] = False

args = cappa.parse(Args, backend=cappa.backend)
```

Note how we also need `dataclasses.field` in order to use `default_factory` since, even though `cappa.Arg` supports `default_factory` as well, we need a value on the right side of the equals sign.

</details>

<details>
<summary> <a href="https://cyclopts.readthedocs.io/en/stable/"><code>cyclopts</code></a> is a very strong <a href="https://typer.tiangolo.com"><code>typer</code></a> alternative that removes much of <code>typer</code>'s reliance on <code>typing.Annotated</code>, at least until you need to specify aliases. <code>typer</code> would have you put the help text in the Annotated field as well, but otherwise, the two would look similar here. Aside from the Annotated usage, the main difference between <code>typer</code>/<code>cyclopts</code> and <code>argspec</code> is that the former hijack your functions, which is incredibly useful for building subcommands but which is just a very different strategy otherwise. Personally, I want a consolidated args object.
</summary>

```py
import os
from pathlib import Path
from cyclopts import Parameter, Token, run
import json
from typing import Any

def json_convert(_: Any, *tokens: Token) -> dict[str, str]:
    return json.loads(" ".join(t.value for t in tokens))

def main(
    path: Path,
    api_key: str = os.environ["SERVICE_API_KEY"],
    limit: Annotated[int, Parameter(alias="-L")] = 10,

    # note that there's actually no sensible value for the RHS default since we know that the value will be provided
    # as dict[str, str] at runtime, so it'll never actually be None
    metadata: Annotated[dict[str, str], Parameter(converter=json_convert, default_factory=dict)] | None = None,
    verbose: Annotated[bool, Parameter(alias="-v")] = False,
    send_notifications: Annotated[bool, Parameter(name=["--send-notifications", "--notif", "-n"])] = False
):
    """
    Parameters
    ----------
    path
        the path to read
    api_key
        the API key to use for the service
    limit
        the max number of times to try doing the thing
    metadata
        metadata for the messages, given as a JSON string
    verbose
        enable verbose logging
    send_notifications
        send all notifications
    """
    assert metadata is not None
    ...


if __name__ == "__main__":
    run(main)
```

</details>

<details>
<summary><a href="https://docs.pydantic.dev/latest/concepts/pydantic_settings/"><code>pydantic-settings</code></a> can also absolutely handle CLI parsing, but it does so within <code>pydantic</code>'s model. This is a strong benefit if you're already using the <code>pydantic</code> framework, but it's a heavy import if you don't need it. Also, because <code>pydantic</code> is meant for such general usage, being able to handle a wide range of sources and formats of data, it forces you into high-level, cross-format abstractions, rather than being tailored for command line ergonomics. In other words, <code>pydantic</code> is way more powerful, but that's at the cost of using a sledgehammer to hang a picture frame.
</summary>

```py
from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Args(BaseSettings, cli_parse_args=True):
    path: Path = Field(description="the path to read")
    api_key: str = Field(validation_alias=AliasChoices("api_key", "SERVICE_API_KEY"))
    limit: int = Field(default=10, validation_alias=AliasChoices("limit", "L"), description="the max number of times to try doing the thing")
    metadata: dict[str, str] = Field(default_factory=dict, description="metadata for the messages, given as a JSON string")
    verbose: bool = Field(default=False, validation_alias=AliasChoices("verbose", "v"), description="enable verbose logging")
    send_notifications: bool = Field(default=False, validation_alias=AliasChoices("send_notifications", "notif", "n"), description="send all notifications")

args = Args()
```

This works, but `validation_alias=AliasChoices(...)` is annoying and requires the original variable name to be listed again as well. It automatically handles the "interpret this field as JSON" by simply type-hinting it as dict, but for literally any other sort of converter, it's so much more work (and now we're typing the field name four separate times):

```py
from pydantic import field_validator, Field, AliasChoices
from pydantic_settings import BaseSettings
from typing import Any

class Args(BaseSettings, cli_parse_args=True):
    values: list[int] = Field(validation_alias=AliasChoices("values", "v"), description="a list of numbers, separated by commas, such as '1,2,3'")

    @field_validator("values", mode="before")
    @classmethod
    def _parse_values(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [int(x) for x in v.split(",")]
        return v
```

And more to the "sledgehammer" point:

```bash
$ uv init --bare test
Initialized project `test` at `/home/user/src/test`

$ cd test

$ uv add pydantic-settings
uv add pydantic-settings
Using CPython 3.14.2+freethreaded interpreter at: /home/user/.local/bin/python3.14
Creating virtual environment at: .venv
Resolved 8 packages in 53ms
Prepared 1 package in 15.46s
Installed 7 packages in 5ms
 + annotated-types==0.7.0
 + pydantic==2.12.5
 + pydantic-core==2.41.5
 + pydantic-settings==2.12.0
 + python-dotenv==1.2.1
 + typing-extensions==4.15.0
 + typing-inspection==0.4.2

# let's check the size of the dependencies
$ du -s .venv/lib/python3.14t/site-packages/* | \
  awk '{ total += $1; } END { print "Total: " total " KiB" }'
Total: 7780 KiB

$ cloc .venv/lib/python3.14t/site-packages/
     182 text files.
     145 unique files.                                          
      38 files ignored.

github.com/AlDanial/cloc v 2.06  T=0.49 s (294.3 files/s, 128010.7 lines/s)
-------------------------------------------------------------------------------
Language                     files          blank        comment           code
-------------------------------------------------------------------------------
Python                         143          10855          14924          37289
Text                             2              0              0              3
-------------------------------------------------------------------------------
SUM:                           145          10855          14924          37292
-------------------------------------------------------------------------------
```

Doing the same with `argspec`:

|                   | dependencies                                                                                      | size (KiB)    | SLOC           |
|-------------------|---------------------------------------------------------------------------------------------------|---------------|----------------|
| argspec           | 2 (argspec, typewire, typing-extensions)                                                                   | 380           | 3,297          |
| pydantic-settings | 7 (pydantic-settings, pydantic, pydantic-core, annotated-types, python-dotenv, typing-inspection, typing-extensions) | 7,780 (20.5×) | 37,292 (11.3×) |

And even then, most of that 3,297 SLOC is just `typing-extensions`. `argspec + typewire` is about 900 SLOC, and since `pydantic-core` is a compiled executable, it's not contributing to the SLOC metric here.

Does it matter? It isn't necessarily a huge issue, but that power isn't free.

```bash
$ hyperfine --warmup 5 --runs 10 "uv run python -c 'import argspec'" "uv run python -c 'import pydantic_settings'"
Benchmark 1: uv run python -c 'import argspec'
  Time (mean ± σ):      81.4 ms ±   2.6 ms    [User: 59.4 ms, System: 21.1 ms]
  Range (min … max):    77.5 ms …  86.5 ms    10 runs
 
Benchmark 2: uv run python -c 'import pydantic_settings'
  Time (mean ± σ):     299.8 ms ±  37.2 ms    [User: 253.6 ms, System: 43.3 ms]
  Range (min … max):   278.5 ms … 403.0 ms    10 runs
 
Summary
  uv run python -c 'import argspec' ran
    3.68 ± 0.47 times faster than uv run python -c 'import pydantic_settings'
```

</details>

## Installation

`argspec` can be easily installed on any Python 3.10+ via a package manager, e.g.:

```bash
# using pip
$ pip install argspec

# using uv
$ uv add argspec
```

The only dependencies are [`typewire`](https://github.com/lilellia/typewire), a small bespoke library I wrote for handling the type conversions and posted independently, and `typing_extensions`.

## Documentation

### `ArgSpec`

Inherit from this class to get the argument parsing functionality. It converts your class to a dataclass and provides a `.from_argv` classmethod that will automatically interpret `sys.argv[1:]` (or you can provide it arguments directly) and give them back to you in their parsed form.

### `ArgumentError`, `ArgumentSpecError`

`ArgumentSpecError` is raised when there's an error with the specification itself. This could be because there are multiple arguments with the same name via aliases or because there are two positional arguments defined as variadic (which is disallowed because it leads to ambiguous and arbitrary parsing), or similar.

`ArgumentError` is raised once the parse is underway when something about the command line arguments that are passed in is invalid. Perhaps an argument is missing or there's an extra argument or it can't be converted to the correct type.

### `positional`, `option`, `flag`

Factory functions to define positional/option/flag argument interfaces. They take the following parameters (note that `T` is the type hint given for the field, and `S` is any type "collapsible" to `T`—see [below](#type-coercion)):

|                                  |                                                                               | **positional** | **option** | **flag**   |
|----------------------------------|-------------------------------------------------------------------------------|----------------|------------|------------|
| `default: S`                     | default value for the argument                                                | ✅              | ✅          | ✅ (T=bool) |
| `default_factory: Callable[[], S]` | zero-argument factory function to call as a default                           | ✅            | ✅          | ❌          |
| `validator: Callable[[S], bool]` | return True if the value is valid, False otherwise                            | ✅              | ✅          | ❌          |
| `converter: Callable[[str], S]` | callable to convert the raw string value to result                             | ✅              | ✅          | ❌          |
| `aliases: Sequence[str]`         | alternative names (long or short) for the option/flag                         | ❌              | ✅          | ✅          |
| `short: bool`                    | whether a short name should automatically be generated using the first letter | ❌              | ✅          | ✅          |
| `long: bool`                     | whether the long name (the field name) should be exposed as a CLI parameter   | ❌              | ✅          | ✅          |
| `negators: Sequence[str]`        | names for flags that can turn the flag "off" e.g., --no-verbose               | ❌              | ❌          | ✅          |
| `help: str \| None`              | the help text for the given argument                                          | ✅              | ✅          | ✅          |

All of these parameters are optional, and all of them (except `default`) are keyword-only.

Notes:

- When `default` is unprovided for `positional` and `option`, it's interpreted as a missing value and must be filled in on the command line; for a flag, `default=False`.
- Providing both `default` and `default_factory` will result in an ArgumentSpecError.
- When using `short=True`, don't also manually provide the short name in `aliases` (such as `name: str = option(short=True, aliases=["-n"])`) as this will result in an ArgumentSpecError for having duplicate names.
- `long=False` allows you to specify an internal variable/field name without exposing it to the users on the command line. Remember to provide another accessor (via `short` or `aliases`); otherwise, an ArgumentSpecError will be raised.
- When a flag's default value is True, a negator is automatically generated. For example, `verbose: bool = flag(True)` generates `--no-verbose` as well.

### `readenv`

This function can be used as a default factory to provide a fallback to a given environment variable if the value is not provided on the command line. It reads the environment variable at instantiation time (i.e., when `.from_argv()` is called), rather than definition time. In particular, the signature is `def readenv(key: str, default: Any = MISSING, *, secret: bool = False) -> Callable[[], Any]` and thus can be used, as in the example at the top of the page, as:

```py
from argspec import ArgSpec, option, readenv

class Args(ArgSpec):
    api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key for the service")
```

If the default parameter is not given (as here), an ArgumentError will be raised if the value is not provided and cannot be found in the environment. Otherwise, the default value is used instead.

Note that the help/usage message for the field will be updated to reflect this fallback:

```text
$ python main.py --help

Usage:
    main.py [OPTIONS] 

Options:
    -h, --help
    Print this message and exit

    --api-key API_KEY <str>
    the API key to use from the service (default: $SERVICE_API_KEY (currently: 'token=demo-api-token'))
```

If `secret=True`, then the help message will *not* show the current value but will instead show `currently: ******`.

### General Notes

### Mutability

By default, `ArgSpec` classes are immutable (via `dataclass(..., frozen=True)`). If you need to have a mutable class, just pass `frozen=False` as part of the subclass definition:

```py
class ImmutableArgs(ArgSpec):
    x: int = positional()

class MutableArgs(ArgSpec, frozen=False):
    x: int = positional()

immutable = ImmutableArgs(x=1)
mutable = MutableArgs(x=1)

with suppress(dataclasses.FrozenInstanceError):
    immutable.x = 2

# but this is totally fine
mutable.x = 2
```

The dataclass being frozen aims to prevent accidental mutation to the class, as most of the time, argv is semantically read-only. This also has the side benefit that the dataclass is hashable by default, meaning that it can be put in set/dict.

The primary purpose for `frozen=False` would be a `__post_init__` that needs to "heal" a broken class:

```py
class Args(ArgSpec, frozen=False):
    min_value: int = positional()
    max_value: int = positional()

    def __post_init__(self):
        if self.min_value > self.max_value:
            sys.stderr.write(f"(min, max) = ({self.min_value}, {self.max_value}) being interpreted as ({self.max_value}, {self.min_value}) instead\n")
            
            # this swap only works because the instance isn't frozen
            self.min_value, self.max_value = self.max_value, self.min_value

args = Args.from_argv(["100", "1"])
print(args)  # Args(min_value=1, max_value=100)
```

#### `--key value` vs. `--key=value`

`argspec` allows for both formats for options. Flags, however, cannot take values even in the latter form. Thus, `--path /path/to/file` and `--path=/path/to/file` are both acceptable, but `--verbose=false` is not (use simply `--verbose` as an enable flag and `--no-verbose` as a disable flag).

#### Type Coercion

`argspec` is both quite lenient with input types but quite strict with output types. That is, if a field is given as `field: T = option(...)`, then once the class has been instantiated, `field` with be of type `T` (even if `T` is a nonleaf type such as `list[int]`). However, since all values on the command line are strings (that is, `sys.argv` is `list[str]`), the values have to be coerced into that type `T`.

In general, `argspec` (through `typewire`) is pretty good about recognising and converting types. `list[str]` can be collapsed into `set[int]` (if the list elements are numeric), for example. However, `str` cannot be naïvely coerced into `dict[str, str]`, and thus, e.g., `converter=json.loads` must be provided.

This leniency also applies to the values in the metadata factory. `default: S`, `default_factory: Callable[[], S]`, and `converter: Callable[[str], S]` are not required to return a value of the hinted type `T`, so long as the value can be coerced into `T` using the regular conversion hooks. Thus, to allow `--vals 1,2,3` to turn into `[1, 2, 3]`, `converter=lambda s: s.split(",")` is sufficient since `list[str] -> list[int]` is collapsible.

Because the type coercion happens *before* the validators, however, `validator` should be `(T) -> bool`.

#### Flexible Naming

`argspec` respects naming conventions. If you define a field as `some_variable`, it'll provide both `--some-variable` and `--some_variable` as valid options on the command line.

In addition, `-h/--help` are provided automatically, but they're not sacred. If you want to define `host: str = option(aliases=["-h"])`, then `argspec` will obey that, mapping `-h/--host` but will still provide `--help`.

#### Validators

`positional` and `option` both define a `validator` parameter. It should be a Callable that takes the desired argument type (not just the raw string value) and returns True if the value is valid and False otherwise. If False, an ArgumentError is raised during the parse.

```py
class Args(ArgSpec):
    path: Path = positional(validator=lambda p: p.exists())
    limit: int = option(validator=lambda limit: limit > 0)

    # Since `Literal` cannot be dynamic, the validator can be used
    # to implement choices in such cases where the values cannot be known in advance:
    # mode: Literal["auto", "manual"] = option()  # <-- prefer this one
    mode: str = option(validator=lambda mode: mode in valid_mode_options)
```

Since the resulting class is a dataclass, you can use `__post_init__` to employ cross-field validation:

```py
class Args(ArgSpec):
    min_value: int = positional()
    max_value: int = positional()

    def __post_init__(self):
        if self.min_value > self.max_value:
            # If you set the class as nonfrozen, so you could also decide to just switch the values in this case (see above).
            raise ArgumentError(f"{self.min_value=} cannot be greater than {self.max_value!r}")

args = Args.from_argv(["10", "100"])
print(args)  # Args(min_value=10, max_value=100)

with suppress(ArgumentError):
    Args.from_argv(["100", "10"])
```

(This is a simple example for illustration, but in this case, it would probably be preferable to use `range: tuple[int, int] = positional(validator=lambda r: r[0] <= r[1])`.)

#### Converters

`positional` and `option` both also define a `converter` parameter. It should be a Callable that takes a singular string (the raw argument value) and returns the processed value to use as the field. An ArgumentError is raised during the parse if (A) an error occurs in this converter or (B) if the resulting value cannot be coerced into the type hint for the field.

```py
@dataclass
class Point:
    x: float
    y: float


def make_points(s: str) -> Iterator[Point]:
    """Make a sequence of Points from a string of the form A,B;C,D;..."""
    for point in s.split(";"):
        x, y = point.split(",")
        yield Point(float(x), float(y))


class Args(ArgSpec):
    metadata: dict[str, int] = option(converter=json.loads)

    # this converter returns list[str], but it will undergo the same
    # type coercion as other values, so it can be interpreted as list[int]
    vals: list[int] = option(converter=lambda s: s.split(","))

    # Point doesn't take a string as an argument, but the converter
    # can force the shape anyway
    # Like vals, this converter is (str) -> Iterator[Point],
    # but it'll be collapsed into tuple[Point] by the parser.
    points: tuple[Point, ...] = option(converter=make_points)

argv = ["--metadata", "{'foo': 1, 'bar': 10}", "--vals", "1,2,3", "--points", "1.0,2.0;3.0,4.0;5.0,6.0"]
args = Args.from_argv(argv)
assert args.metadata == {"foo": 1, "bar": 10}
assert args.vals == [1, 2, 3]
assert args.points == [Point(1.0, 2.0), Point(3.0, 4.0), Point(5.0, 6.0)]
```

> [!NOTE] When `converter` is given, the parser always **consumes exactly one value**, regardless of the type hint. Thus, `vals: list[int] = option(converter=lambda s: s.split(","))` will take `--vals 1,2,3 4,5,6` to just `[1, 2, 3]` and leave `"4,5,6"` as a positional value.

#### Type Inference

`argspec` infers as much as it can from the type hints you give it.

```py
class Args(ArgSpec):
    # --port PORT, required (because no default is provided), will be cast as int
    port: int = option()

    # --coordinate COORDINATE COORDINATE, required, will take two values, both cast as float
    coordinate: tuple[float, float] = option()

    # --mode MODE, not required (defaults to 'auto'), will only accept one of the given values
    mode: Literal["auto", "manual", "magic"] = option("auto")

    # --names [NAME ...], not required, will take as many values as it can
    names: list[str] = option()
```

#### Direct Instantiation

In the case where you want to use class as a raw dataclass, perhaps for testing, you can do so, with the same runtime guarantees about type coercion and defaults:

```py
def seven() -> int:
    return 7

class Args(ArgSpec):
    x: int = option()
    y: int = option(2)
    z: int = option(default_factory=seven)


with suppress(TypeError):
    # x is required but unprovided, so this is a TypeError
    Args()

# fallback to defaults
print(Args(1))    # Args(x=1, y=2, z=7)

# coerce types even if provided...
print(Args("1"))  # Args(x=1, y=2, z=7)

# ...unless they can't be coerced
with suppress(ValueError):
    Args(x="invalid")

# if you really want to disable validation (though defaults will still get applied)
print(Args(x="1", y="invalid", __ARGSPEC_SKIP_VALIDATION__=True))  # Args(x='1', y='invalid', z=7)
```

#### Look-Ahead Variadics

When defining variadic (variable-length) arguments, `argspec` will happily look ahead to see how many values it can safely take whilst still leaving enough for the later arguments. For example:

```py
class Args(ArgSpec):
    head: str = positional()
    middle: list[str] = positional()
    penultimate: str = positional()
    tail: str = positional()
    and_two_more: tuple[str, str] = positional()

args = Args.from_argv(["A", "B", "C", "D", "E", "F", "G"])
print(args)  # Args(head='A', middle=['B', 'C'], penultimate='D', tail='E', and_two_more=('F', 'G'))
```

However, this requires that *at most one* positional argument be defined as variadic. If multiple positionals are variadic, this is an ArgumentSpecError.

#### Mutable Defaults

`argspec` automatically recognises mutable default values and converts them under the hood to default factories. Thus, the following two field specifications are equivalent.

```py
class Args(ArgSpec):
    x: list[int] = option([1, 2, 3])
    y: list[int] = option(default_factory=lambda: [1, 2, 3])


args1 = Args.from_argv(argv=None)
args2 = Args.from_argv(argv=None)

print(args1.x)  # [1, 2, 3]

args2.x.append(4)

print(args1.x)  # [1, 2, 3]
print(args2.x)  # [1, 2, 3, 4]
```

## Known Limitations

- `argspec` does not provide a mechanism for subcommands or argument groups (such as mutually exclusive arguments)
- `argspec` does not yet support combined short flags (i.e., `-a -b -c` cannot be shortened to `-abc`)
- Static analysis support for the generated `__init__` method (used for direct instantiation) is inconsistent across IDEs depending on their implementation of `@dataclass_transform()` ([PEP 681](https://peps.python.org/pep-0681/)).
  - Pyright seems to generally provide strong support, providing full autocomplete and typing for fields and showing complete signatures (e.g., `(x: int = positional(help="the value of x"), y: int = positional(2, help="the value of y")) -> Args`).
  - Pylance (VSCode) provides full autocomplete and typing for fields, but it may fall back to generic `class Args()` in tooltips when directly instantiating.
  - mypy provides a correct analysis of the types on the resulting class and, regarding direct instantiation, will catch both invalid types (`Args(x='1')` -> arg-type) and invalid parameters (`Args(z=7)` -> call-arg).
