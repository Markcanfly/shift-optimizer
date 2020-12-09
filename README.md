# shift-optimizer

A shift optimizer, intended for use with small-to-medium sized groups.

Built upon the fantastic [CP-SAT Solver](https://developers.google.com/optimization/cp/cp_solver) by Google.

## What it does
Takes a list of work shifts, along with a list of personal preferences, and tries to find an optimal assignment for everyone. 

## CLI
```shell
$ python main.py -h
usage: main.py [-h] [-o TO_FILE] prefs shifts target_hours hours_deviance long_shifts

positional arguments:
  prefs                 Name of the csv file containing the user-submitted preferences.
  shifts                Name of the json file containing the shifts.
  target_hours          The number of hours to set as goal
  hours_deviance        The maximum number of hours each employee's weekly work hours can deviate.
  long_shifts           The minimum number of long shifts each person needs to have.

optional arguments:
  -h, --help            show this help message and exit
```

## Constraints
*Note: the following parameters can be given to the solver from the CLI.*

// TODO

## Input formats

*shifts:*  A json file, structured as such: 
```json
{
    "Monday 12.01.": [
    {
            "capacity": 1,
            "begin": [
                8,
                45
            ],
            "end": [
                16,
                0
            ]
        }, ...
    ],
    "Tuesday 12.02.": [
        ...
    ]
}
```
*preferences*: a csv file, structured as such:
Name        | day0       | day1 | ...
---         | ---        | ---  | ---
John Cleese | 2, 3, 1, 5 | 0, 1 | ...

*Note: the table headers will be ignored, but the number of days must match.*
