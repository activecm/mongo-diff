#!/usr/bin/env python3

from pymongo import MongoClient
import sys
import bson

NO_ARRAY_ORDER = False

def count_unique_values(field_name, coll):
    #abominations to get mongo to count how many distinct values
    #exist for a field
    pipeline = [
        {"$project": { field_name: 1 } },
        {"$group": { "_id": "$" + field_name } },
        {"$project": { "dummy": "dummy" } },
        {"$group": { "_id": "dummy", "count": { "$sum": 1 } } }
    ]
    results = list(coll.aggregate(pipeline))
    if len(results) == 0:
        return 0
    return results[0]["count"]


def select_best_index(coll):
    # get a sample from the collection
    sample_item = list(coll.find(limit=1))

    # if there is no data in the collection, return None
    if len(sample_item) == 0:
        return None

    sample_item = sample_item[0]

    # get a copy of the index info
    index_information = coll.index_information()

    # get rid of multi key indexes
    toDelete = []
    for key, value in index_information.items():
        if len(value["key"]) > 1:
            toDelete.append(key)

    # get rid of ObjectID
    for key, value in index_information.items():
        field_name = value["key"][0][0]
        if field_name in sample_item and isinstance(sample_item[field_name], bson.objectid.ObjectId):
            toDelete.append(key)

    for key in toDelete:
        del index_information[key]

    # no candidate indexes
    if len(index_information) == 0:
        # just choose the first non ObjectID field
        for key, value in sample_item:
            if not isinstance(value, bson.objectid.ObjectID):
                return key
        # no non ObjectID fields....
        return None

    # search for a unique index
    for index in index_information.values():
        if "unique" in index:
            return index["key"][0][0]

    best_index = None
    best_index_count = 0
    for index in index_information.values():
        field_name = index["key"][0][0]
        index_count = count_unique_values(field_name, coll)
        if index_count > best_index_count:
            best_index = field_name
            best_index_count = index_count

    return best_index


def compare_entries(db1_entry, db2_entry):
    # If there are keys in one entry but not the other, return false
    if len(set(db1_entry.keys()) ^ set(db2_entry.keys())) > 0:
        return False

    for key, db1_value in db1_entry.items():
        if isinstance(db1_value, bson.objectid.ObjectId):
            continue
        db2_value = db2_entry[key]
        if isinstance(db2_value, float):
            same = abs(db1_value - db2_value) < 0.01
        elif isinstance(db2_value, list) and NO_ARRAY_ORDER:
            same = set(db1_value) == set(db2_value)
        else:
            same = db1_value == db2_value
        if not same:
            return False

    return True


def main():
    if (len(sys.argv) != 4):
        print("./mongo-diff.py <host> <db1> <db2>")
        return 1
    HOST = sys.argv[1]
    DB1  = sys.argv[2]
    DB2  = sys.argv[3]

    mgo = MongoClient(HOST)

    db1 = mgo[DB1]
    db2 = mgo[DB2]

    print("Comparing databases: {0} and {1}".format(DB1, DB2))
    db1_coll_names = db1.collection_names()
    db2_coll_names = db2.collection_names()

    if (len(db1_coll_names) != len(db2_coll_names)):
        print("Databases contain a different number of collections")
        return 1

    if not all([x in db2_coll_names for x in db1_coll_names]):
        print("Databases contain different collections")
        return 1


    collection_match = {}

    for coll in sorted(db1_coll_names)[::-1]:
        print("Comparing collection: {0}".format(coll))
        errors = [] # List of errors
        match_count = 0 # How many records in DB1 match DB2
        collection_counts = (0, 0) # How many records are in DB1.coll and DB2.coll

        skip_matching = False # If there's no data or missing indexes

        db1_indexes = db1[coll].index_information()
        db2_indexes = db2[coll].index_information()
        if not all(x in db2_indexes.keys() for x in db1_indexes.keys()):
            errors += ["{0}.{1} and {2}.{3} contain differing indexes".format(DB1, coll, DB2, coll)]
            skip_matching = True

        collection_counts = (db1[coll].count(), db2[coll].count())

        if collection_counts[0] != collection_counts[1]:
            errors += ["{0}.{1} contains {2} records while {3}.{4} contains {5} records".format(DB1, coll, collection_counts[0], DB2, coll, collection_counts[1])]

        if collection_counts[0] == 0:
            print("\t{0}.{1} is empty".format(DB1, coll))
            skip_matching = True

        if not skip_matching:
            best_field = select_best_index(db2[coll])

            print("\tSelecting field {0} for searching {1}.{2}".format(best_field, DB2, coll))

            percent_update_interval = 0.05
            last_percent_update = -percent_update_interval
            search_count = 0
            for db1_entry in db1[coll].find():
                db1_best_field_value = db1_entry[best_field]
                found = False
                try:
                    for db2_entry in db2[coll].find({best_field: db1_best_field_value}):
                        found = compare_entries(db1_entry, db2_entry)
                        if found:
                            match_count += 1
                            break

                except bson.errors.InvalidBSON:
                    errors += ["Unicode error while iterating over {0}.{1}".format(DB1, coll)]

                if not found:
                    errors += ["Record in {0}.{1} did not match any record in {2}.{3}\n{4}".format(DB1, coll, DB2, coll, db1_entry)]

                search_count += 1
                search_percent = search_count / collection_counts[0]
                if search_percent - last_percent_update >= percent_update_interval:
                    print("\t{0:.0f}% finished comparing {1}.{2} to {3}.{4}".format(search_percent * 100, DB1, coll, DB2, coll))
                    last_percent_update = search_percent

        print("\t{0:.0f}% finished comparing {1}.{2} to {3}.{4}".format(100, DB1, coll, DB2, coll))
        print("\tMatched {0} records out of {1} from {2}.{3} to records in {4}.{5}".format(match_count, collection_counts[0], DB1, coll, DB2, coll))
        for err in errors:
            print("\t" + err)

        if len(errors) != 0:
            collection_match[coll] = False
        else:
            collection_match[coll] = True

    if not all(collection_match.values()):
        return 1

    print("Databases match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
