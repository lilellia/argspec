# CHANGELOG

## v0.3.0

- Add support for `--key=value` (and `-k=value`) syntax for option arguments. Note that this does not allow flags to take arguments: `--verbose=true` is an ArgumentError.

## v0.2.0

- Fixed help messages to include automatic short aliases (which had worked but weren't documented)
- Only provide default `--no-X` flag negators for `default=True` flags when no other negator was provided

## v0.1.0

- Initial release
