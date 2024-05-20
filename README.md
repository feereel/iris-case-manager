# IRIS CASE MANAGER (v2.3.7)

## Instalation and update

In your shuffle admin panel click on Apps. After that, next to active applications click on icon download from Github.

1. Into repository paste: https://github.com/feereel/iris-case-manager
2. Into branch write: main
3. Click on Submit

## Api

### Export case

Exports a case from iris to shuffle file storage.

- Apikey - Сan be obtained from your iris instance. Click on your profile -> My settings -> Copy API Key.
- Cid - Id of the case that will be exported.
- Host - Your iris instance host. Must start with: https:// or http://
- Agent
- Ssl verify

<strong>Returns</strong>
```json
{
  "success": true,
  "file_ids": [
    "file_4863a408-affc-4ec2-ba8e-2d778bba840d"
  ]
}
```

### Export all cases

Exports all cases from iris to shuffle file storage.

- Apikey - Сan be obtained from your iris instance. Click on your profile -> My settings -> Copy API Key.
- Host - Your iris instance host. Must start with: https:// or http://
- Agent
- Ssl verify
- In one file - If true all cases will be stored in one zip file otherwise each case in separate file

<strong>Returns (in one file == true)</strong>
```json
{
  "success": true,
  "file_ids": [
    "file_51c96ced-5008-4e86-909c-4c5b1acac1e4"
  ]
}
```

<strong>Returns (in one file == false)</strong>
```json
{
  "success": true,
  "file_ids": [
    "file_6571cecb-6e4e-49f0-826d-e7d35898b806",
    "file_eeb780bf-6c27-4d7a-9888-27097a0414f0"
  ]
}
```


### List all cases

List all iris cases ids.

- Apikey - Сan be obtained from your iris instance. Click on your profile -> My settings -> Copy API Key.
- Cid - Id of the case that will be exported.
- Host - Your iris instance host. Must start with: https:// or http://
- Agent
- Ssl verify

<strong>Returns</strong>
```json
{
  "success": true,
  "cases_ids": [
    1,
    2
  ]
}
```


### Import case

Import case to Iris by file id from shuffle storage 

- Apikey - Сan be obtained from your iris instance. Click on your profile -> My settings -> Copy API Key.
- Host - Your iris instance host. Must start with: https:// or http://
- File id - File id from shuffle storage (zip with cases)
- Publisher name - Name of iris customer which creates a case
- Agent
- Ssl verify

<strong>Returns</strong>
Returns uuid4 of a case in pushed if success.

```json
{
  "success": true,
  "pushed": [
    "3dbba6f1-ab4a-4649-969c-041b434f0ed1",
    "180f616a-d3bd-4cf8-8b3a-8e6d14e27e53"
  ],
  "skipped_by_dump": [],
  "skipped_by_validation": [],
  "skipped_by_push": []
}
```

## Case zip structure

All cases stored in folder named "Cases".
Each case is separated in folder named with uuid4. Inside it case.json contains everything needed to restore case with dependencies. Other files are needed for the datastore.

<strong>Example</strong>
```
Cases
├── 228e2b5b-bac6-4604-9931-53960a3a0dff
│   └── Case 1
│       ├── Evidences
│       ├── Files_from_another_case_1
│       ├── IOCs
│       ├── Images
│       └── case.json
├── 541629a7-c4f4-4d0c-aa41-4620f2eb145f
│   └── Case 2
│       ├── Evidences
│       │   └── cowboy.jpg
│       ├── Files_from_another_case_2
│       ├── Files_from_another_case_4
│       ├── IOCs
│       ├── Images
│       │   └── task.png
│       └── case.json
├── ce7b7fac-f5c8-42a1-946b-7df3ae257f59
│   └── Case 2
│       ├── Evidences
│       ├── Files_from_another_case_2
│       ├── IOCs
│       ├── Images
│       └── case.json
└── ff4c011b-c2a1-4d61-a1bc-f5178bfd409f
    └── Case 1
        ├── Evidences
        ├── Files_from_another_case_1
        ├── Files_from_another_case_3
        ├── IOCs
        ├── Images
        └── case.json
```
