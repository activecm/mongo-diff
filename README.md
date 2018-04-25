# MongoDiff

MongoDiff checks whether two MongoDB databases are the same (including indexes).

NOTE: The `_id` field is ignored since it is assumed to be unique.

# Usage
`mongo-diff.py <uri> <database 1> <database 2>`

MongoDiff exits with status 0 if the databases are the same and 1 if they are not.

# Dependencies

- Python3
- PyMongo

# Notes

For best performance, ensure a unique index exists in each collection for the dataset being compared. If a unique index does not exist, MongoDiff will attempt to find the index with the most unique values.

If no index exists other than \_id, performance will degrade to O(n^2)
