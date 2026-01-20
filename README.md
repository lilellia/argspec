# argspec

A library for cleanly and succinctly performing type-safe command-line argument parsing via a declarative interface.

## Why `argspec`?

I view argument parsing as "the bit that happens before I can actually run my code". It's not part of my problem solving. It's literally just boilerplate to get information into my program so that my program can do its thing. As a result, I want it to be as minimal and as painless as possible. `argspec` aims to make it as invisible as possible without being magic.

```py
from argspec import ArgSpec, positional, option, flag
from pathlib import Path

class Args(ArgSpec):
    path: Path = positional(help="the path to read")
    limit: int = option(10, aliases=["-L"], help="the max number of tries to try doing the thing")
    verbose: bool = flag(short=True, help="enable verbose logging")  # flags default to False, and short=True gives the -v alias
    send_notifications: bool = flag(aliases=["-n", "--notif"], help="send all notifications")

args = Args.from_argv()  # <-- .from_argv uses sys.argv[1:] by default, but you can provide a list manually if you want
print(args)  # <-- an object with full type inference and autocomplete
```

Of course, you also get a help message (accessible manually by `Args.__argspec_schema__.help()`, but automatically printed with `-h/--help` or on SystemExit from an ArgumentError):

```bash
$ python main.py --help

# Usage:
#     main.py [OPTIONS] PATH

# Options:
#     --help, -h
#     Print this message and exit (default: False)

#     --verbose
#     enable verbose logging (default: False)

#     -n, --notif, --send-notifications
#     send all notifications (default: False)

#     -L, --limit LIMIT <int>
#     the max number of tries to try doing the thing (default: 10)


# Arguments:
#     PATH <Path>
#     the path to read
```

`ArgSpec` (the class) is built on top of `dataclasses`, so you also get all of the dataclass functions (`__init__`, `__repr__`, etc.) for free:

```py
print(args)  # Args(path=Path('/path/to/file'), limit=10, verbose=False, send_notifications=False)
```

### Why not `argparse`?

`argparse` belongs to the standard library and is sufficient for most situations, but while it's capable, it's verbose through it's imperative style and does not allow for type inference and autocomplete.

```py
from argparse import ArgumentParser
from pathlib import Path

parser = ArgumentParser()
parser.add_argument("path", type=Path, help="the path to read")
parser.add_argument("-L", "--limit", type=int, default=10, help="the max number of times to try doing the thing")
parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")
parser.add_argument("-n", "--notif", "--send-notifications", action="store_true", help="send all notifications")

args = parser.parse_args()
print(args.notifications)  # <-- AttributeError, but you don't get any help from your IDE
```

If you want type safety, you can do something like this:

```py
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Self

@dataclass
class Args:
    path: Path
    limit: int
    verbose: bool
    send_notifications: bool


    @classmethod
    def from_argv(cls) -> Self:
        parser = ArgumentParser()
        parser.add_argument("path", type=Path, help="the path to read")
        parser.add_argument("-L", "--limit", type=int, default=10, help="the max number of times to try doing the thing")
        parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")
        parser.add_argument("-n", "--notif", "--send-notifications", action="store_true", help="send all notifications")

        return cls(**vars(parser.parse_args()))

args = Args.from_argv()
print(args.send_notifications)  # <-- You do get autocomplete for this
```

But, obviously, that's a pain, and you now have to define your arguments twice, which is a recipe for forgetting to update it in one of those places.

### Why not `typer`?

`typer` is probably the most popular argparse alternative, but it achieves its parsing goals by hijacking your function calls and injecting values into the signature. Plus, for basic uses, it's pretty clean, but for even just nontrivial examples...

```py
from pathlib import Path
from typing import Annotated

import typer

def main(
    path: Annotated[Path, typer.Argument(help="the path to read")],
    limit: Annotated[int, typer.Option("--limit", "-L", help="the max number of times...")] = 10,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="enable verbose logging")] = False,
    send_notifications: Annotated[
        bool, 
        typer.Option("--send-notifications", "--notif", "-n", help="send all notifications")
    ] = False,
):
    print(f"Path: {path}, Limit: {limit}, Verbose: {verbose}")

if __name__ == "__main__":
    typer.run(main)
```

That's certainly also pretty messy, what with all of the `typing.Annotated` calls everywhere and your function having a long signature with lots of parameters. You also don't get a consolidated `args` object this way, which may or may not be a benefit, depending on who you ask. (Personally, I want the consolidated object.)

That said, one thing `typer` is genuinely fantastic at is subcommands because it wants to use your functions anyway.

## Installation

`argspec` can be easily installed on any Python 3.10+ via a package manager, e.g.:

```bash
# using pip
$ pip install argspec

# using uv
$ uv add argspec
```

The only dependencies are [typewire](https://github.com/lilellia/typewire), a small bespoke library I wrote for handling the type conversions and posted independently, and `typing_extensions`.

## Documentation

### `ArgSpec`

Inherit from this class to get the argument parsing functionality. It converts your class to a dataclass and provides a `.from_argv` classmethod that will automatically interpret `sys.argv[1:]` (or you can provide it arguments directly) and give them back to you in their parsed form.

### `ArgumentError`, `ArgumentSpecError`

`ArgumentSpecError` is raised when there's an error with the specification itself. This could be because there are multiple arguments with the same name via aliases or because there are two positional arguments defined as variadic (which is disallowed because it leads to ambiguous and arbitrary parsing), or similar.

`ArgumentError` is raised once the parse is underway when something about the command line arguments that are passed in is invalid. Perhaps an argument is missing or there's an extra argument or it can't be converted to the correct type.

### `positional`, `option`, `flag`

Factory functions to define positional/option/flag argument interfaces. They take the following parameters:

|                                  |                                                                               | **positional** | **option** | **flag**   |
|----------------------------------|-------------------------------------------------------------------------------|----------------|------------|------------|
| `default: T`                     | default value for the argument                                                | ✓              | ✓          | ✓ (T=bool) |
| `validator: Callable[[T], bool]` | return True if the value is valid, False otherwise                            | ✓              | ✓          | ✕          |
| `aliases: Sequence[str]`         | alternative names (long or short) for the option/flag                         | ✕              | ✓          | ✓          |
| `short: bool`                    | whether a short name should automatically be generated using the first letter | ✕              | ✓          | ✓          |
| `negators: Sequence[str]`        | names for flags that can turn the flag "off" e.g., --no-verbose               | ✕              | ✕          | ✓          |
| `help: str \| None`              | the help text for the given argument                                          | ✓              | ✓          | ✓          |

All of these parameters are optional, and all of them (except `default`) are keyword-only.

Notes:

- When `default` is unprovided for `positional` and `option`, it's interpreted as a missing value and must be filled in on the command line; for a flag, `default=False`.
- When using `short=True`, don't also manually provide the short name in `aliases` (such as `name: str = option(short=True, aliases=["-n"])`) as this will result in an ArgumentSpecError for having duplicate names.
- When a flag's default value is True, a negator is automatically generated. For example, `verbose: bool = flag(True)` generates `--no-verbose` as well.

### General Notes

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

However, this requires that *at most one* positional argument be defines as variadic. If multiple positionals are variadic, this is an ArgumentSpecError.

## Known Limitations

- `argspec` does not provide a mechanism for subcommands or argument groups (such as mutually exclusive arguments)
- `argspec` does not yet support combined short flags (i.e., `-a -b -c` cannot be shortened to `-abc)
