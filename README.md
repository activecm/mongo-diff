# MongoDiff

MongoDiff checks whether two MongoDB databases are the same (including indexes).

NOTE: All ObjectId fields are ignored since they are assumed to be unique to each database.

# Usage
`mongo-diff.py <uri> <database 1> <database 2> 2>unmatched-records`

MongoDiff exits with status 0 if the databases are the same and 1 if they are not.

Stdout displays a human readable status information and a report on
how many records matched in each collection.

Stderr displays a line separated list of records in `<database 1>`
which were not found in `<database 2>`

# Dependencies

- Python3
- PyMongo

# Notes

For best performance, ensure a unique index exists in each collection for the dataset being compared. If a unique index does not exist, MongoDiff will attempt to find the index with the most unique values.

If no index exists other than \_id, performance will degrade to O(n^2)

MongoDiff will refuse to use any indexes which contain a field with type ObjectId.
