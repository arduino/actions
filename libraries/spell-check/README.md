# libraries/spell-check action

Runs codespell on library source code and examples contained in the library.

## Inputs

### `ignore-words-list`

File path of list of words to ignore.

### `skip-paths`

Comma-separated list of files to skip. It accepts globs as well. `./.git` is always skipped.

## Example usage

```yaml
uses: arduino/actions/libraries/spell-check@master
```
