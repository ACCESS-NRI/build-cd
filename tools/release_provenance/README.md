
# Save release data to database
`save_release.py` is used to save release data to the database. It takes a release data JSON file as input in the format described in `test_release_data.json`.
To save the release data to the database, run the following command:

```
python save_release.py test_release_data.json
```

## Update Model Status
To update the model status, run the following command:

```
python update_model_status.py <spack_hash_of_model> <status>
```
The `status` can be `active`, `retracted`, `eol` or `deleted`.