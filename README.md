# OTA File Service

## Overview

OTA File Service enables users to upload files to the cloud and deploy files to robots. This repo includes a cloud service with APIs to upload, deploy and manage files and a daemon running on the robot to download files and report deployment states.  

## Components
### S3 Storage
All files are stored in a S3 storage. 
### Cloud Service
The cloud service provides APIs to upload, deploy and manage files. The server communicates with the daemon running on the robot through MQTT. By default, the cloud server sends file deployment jobs on topic `ota/<robot_id>/deploy` and receives job states on topic `ota/<robot_id>/state`. If the robot daemon is offline, the cloud server will keep incompleted jobs and retry when the robot is back online.
### Daemon
A daemon running on the robot to process file deployment jobs and report states through MQTT. By default, the daemon receives file deployment jobs on topic `ota/<robot_id>/deploy` and sends job states on topic `ota/<robot_id>/state`. This daemon is added to `nova_init` as a systemd service named `nova-isaac-ota`.
## Get Started
Before initiating the deployment process, ensure you have the necessary credentials and configuration details for your S3 storage. You will need the following information:  
  * `aws_access_key_id`: The access key ID that uniquely identifies your AWS account.
  * `aws_secret_access_key`: The secret access key for secure communication with AWS services.
  * `endpoint_url`: The endpoint URL of the S3 service, which may vary based on the region or if using a custom S3-compatible service.
  * `region_name`: The AWS region in which your S3 bucket is located.
  * `bucket_name`: You should create at least one bucket to hold your files. `bucket_name` is needed when uploading files.  
  
To deploy the cloud service on a server and enable the daemon on a robot, follow these steps below:
### For Deployment
#### 1. Deploy the cloud services  
   In the file `docker-compose/.env`, provide values for `S3_ID`, `S3_ACCESS_KEY` and `S3_ENDPOINT_URL` and run the following
   ```
   cd docker-compose
   docker compose -f bringup_services.yaml up
   ```
   Access service APIs on http://localhost:9005/api/v1/docs  
   
#### 2. Launch the daemon  
For NOVA Carter with the latest nova_init installed, the daemon is installed as a systemd service named `nova-isaac-ota`.  For the first run, modify the config file `/opt/nvidia/nova/isaac_cloud/ota-deamon-config.yaml`. Here is an example.
  ```yaml
   # S3 config
   region_name: us-east-1
   endpoint_url: <aws_endpoint_url>
   aws_access_key_id: <aws_access_key_id>
   aws_secret_access_key: <aws_secret_access_key>
   # MQTT Host
   host: <cloud service ip>
   # Robot info
   robot_id: <robot_id>
   cloud_service_url: http://<cloud service ip>:9005/api/v1
   ```  
You should provide S3 information and robot_id. `<cloud service ip>` is the ip where you deploy the cloud service.  
After configuration, you can restart the service
```
sudo systemctl restart nova-isaac-ota
```

For a general robot, follow the steps below to build an executable and run the daemon.  

1. Build the daemon executable  
   1. Enter development docker container
    ```
    cd ota-file-service
    ./scripts/run_dev.sh
    ```
   2. Within the container, run build command and exit the container
   ```
    bazel build //daemon:daemon_onedir
    exit
   ```
   3. The executable is generated in `./bazel-bin/daemon/ota_daemon_onedir/ota-daemon`.

   >**Note:** The executable generated is specific to the operating system. Therefore, the steps above should be performed on the same operating system that will be used to run the executable.

2. Create a config file with the following fields on the robot at `/etc/ota-config.yaml`. You should provide S3 information and robot_id. `<cloud service ip>` is the ip where you deploy the cloud service.
   ```yaml
   # S3 config
   region_name: us-east-1
   endpoint_url: <aws_endpoint_url>
   aws_access_key_id: <aws_access_key_id>
   aws_secret_access_key: <aws_secret_access_key>
   # MQTT Host
   host: <cloud service ip>
   # Robot info
   robot_id: <robot_id>
   cloud_service_url: http://<cloud service ip>:9005/api/v1
   ```
3. Run the daemon 
   ```
    ./bazel-bin/daemon/ota_daemon_onedir/ota-daemon --config /etc/ota-config.yaml
   ```

### For Local Development
   
The service works with a Postgres database, a MQTT broker and an S3 object storage. Here are steps to launch the service and its dependencies

1. Postgres database
    ```
    export POSTGRES_USER=<username>
    export POSTGRES_PASSWORD=<password>
    ```
    ```
    docker run --rm --name postgres \
      --network host \
      -e POSTGRES_USER=$POSTGRES_USER \
      -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
      -e POSTGRES_DB=file \
      -d postgres:14.5
    ```

2. MQTT Broker
    ```
    cd ota-file-service
    docker run -it --network host -v ${PWD}/app/tests/test_utils/mosquitto.sh:/mosquitto.sh -d eclipse-mosquitto:latest sh mosquitto.sh 1883 9001
    ```

3. OTA Service

    Launch the developer Docker container
    ```
    cd ota-file-service
    ./scripts/run_dev.sh
    ```
    Run the service
    ```
    POSTGRES_PASSWORD=<password> POSTGRES_USER=<username> S3_ACCESS_KEY=<aws_secret_access_key> S3_ID=<aws_access_key_id> S3_ENDPOINT_URL=<s3_endpoint_url>  bazel run //app:ota-file-service -- --config ${PWD}/app/config/defaults.yaml
    ```

    Access service APIs on http://localhost:9005/api/v1/docs

4. OTA Daemon  
    In a new terminal, enter developer docker container
    ```
    cd ota-file-service
    ./scripts/run_dev.sh
    ```
    In the development docker container  
    ```
    S3_ACCESS_KEY=<aws_secret_access_key> S3_ID=<aws_access_key_id> S3_ENDPOINT_URL=<s3_endpoint_url> ROBOT_ID=<robot_id> bazel run //daemon:ota-file-daemon -- --config ${PWD}/daemon/config/defaults.yaml
    ```

## API reference

### POST</code> <code><b>/file/upload</b></code>
Upload a list of files to the S3 storage and keep their metatdata.

<details><summary>Parameters</summary>

#### file_info_list `object`
Required. Information of the files to upload.
<details><summary>object properties</summary>

##### file_info_list.file_list `array of objects`
    
An array of file_info object. Here are object properties:
##### s3_bucket `string`  
  Required. S3 bucket that stores the file. 
##### s3_object_name `string`
  Optional. S3 object name of the file. If not provided, the service will generate one in the form of <file_name>_<UUID>.
##### robot_id `string`
  Optional. The robot identifier associated with the file.
##### robot_type `string`
  Optional. The robot type associated with the file.
##### deploy_path `string`
  Optional. The path where the file should be deployed by default.
##### file_metadata `dict`
  Optional. A key-value map for customized metadata. For example, {"type": "image", "author": "Bob"}. 

</details>

#### files `array of files`
Required. A list of files to upload. The number of files should be the same as the length of `file_info_list.file_list`
</details>

<details><summary>Example cURL</summary>

```
curl -X 'POST' \
  'http://127.0.0.1:9005/api/v1/file/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file_info_list={
  "file_list": [
    {
      "s3_bucket": "files",
      "robot_id": "robot01",
      "file_metadata": {"type": "test"}
    }
  ]
}' \
  -F 'files=@test.txt;type=text/plain'
```
</details>

### GET</code> <code><b>/file/list</b></code>
Return a list of FileInfo objects according to search criteria. The files are returned sorted by creation date, with the most recently created files appearing first.

<details><summary>Parameters</summary>

#### s3_bucket `string`  
  Optional. S3 bucket that stores the file. 
#### s3_object_name `string`
  Optional. S3 object name of the file.
#### robot_id `string`
  Optional. The robot identifier associated with the file.
#### robot_type `string`
  Optional. The robot type associated with the file.
#### deploy_path `string`
  Optional. The path where the file should be deployed by default. Provided when uploading the file.
#### file_metadata `string`
  Optional. A key-value dictionary. For example, {"type": "image"}. Provided when uploading the file.
</details>
<details><summary>Example cURL</summary>

```
curl -X 'GET' \
  'http://localhost:9005/api/v1/file/list?robot_id=robot01'
```
</details>

### POST</code> <code><b>/file/deploy</b></code>
Deploy a list of files on the robot. The API will first upload the files to S3 storage and then deploy them on the robot.

<details><summary>Parameters</summary>

#### file_info_list `object`
Required. Information of the files to upload.
<details><summary>object properties</summary>

##### file_info_list.file_list `array of objects`
    
An array of file_info object. Different from `/file/upload` API, `robot_id` and `deploy_path` are required. Here are object properties:
##### s3_bucket `string`  
  Required. S3 bucket that stores the file. 
##### s3_object_name `string`
  Optional. S3 object name of the file. If not provided, the service will generate one in the form of <file_name>_<UUID>.
##### robot_id `string`
  Required. The robot identifier to deploy the file.
##### robot_type `string`
  Optional. The robot type associated with the file.
##### deploy_path `string`
  Required. The path where the file should be deployed.
##### file_metadata `dict`
  Optional. A key-value map for customized metadata. For example, {"type": "image", "author": "Bob"}. 

</details>

#### files `array of files`
Required. A list of files to upload. The number of files should be the same as the length of `file_info_list.file_list`
</details>

<details><summary>Example cURL</summary>

```
curl -X 'POST' \
  'http://127.0.0.1:9005/api/v1/file/deploy' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file_info_list={
  "file_list": [
    {
      "s3_bucket": "files",
      "robot_id": "robot01",
      "deploy_path": "/tmp/test.txt"
    }
  ]
}' \
  -F 'files=@test.txt;type=text/plain'
```
</details>

### POST</code> <code><b>/file/deploy_from_s3</b></code>
Deploy an uploaded file to a robot given file location in S3 and robot identifier. In instances where the `deploy_path` is unset, the file will be deployed to the deploy_path provided in the file upload API call. Should this default path not be defined, the API will terminate with an error.

<details><summary>Parameters</summary>

#### s3_bucket `string`  
  Required. S3 bucket that stores the file. 
#### s3_object_name `string`
  Required. S3 object name of the file.
#### robot_id `string`
 Required. The robot identifier to deploy the file.
#### deploy_path `string`
  Optional. The path where the file should be deployed. If not set, the file will be deployed to the path provided when uploading the file.
</details>

<details><summary>Example cURL</summary>

```
curl -X 'POST' \
  'http://127.0.0.1:9005/api/v1/file/deploy_from_s3?robot_id=robot01&s3_bucket=files&s3_object_name=test.txt_bdc28a7a-d504-47d9-84b8-bfc07667cea7&deploy_path=%2Ftmp%2Fdeploy' 
```
</details>

### GET</code> <code><b>/file/download</b></code>
Download an uploaded file.

<details><summary>Parameters</summary>

#### s3_bucket `string`  
  Required. S3 bucket that stores the file. 
#### s3_object_name `string`
  Required. S3 object name of the file to download.
</details>

<details><summary>Example cURL</summary>

```
curl -X 'GET' \
  'http://127.0.0.1:9005/api/v1/file/download?s3_object_name=test.txt_bdc28a7a-d504-47d9-84b8-bfc07667cea7&s3_bucket=files'
```
</details>

### PATCH</code> <code><b>/file/update</b></code>
Update the content or attributes of an uploaded file.  
**Note:** This API does not update the files deployed on the robot. You have to call `POST /file/deploy_from_s3` to update files on the robot.

<details><summary>Parameters</summary>

#### file_info `object`
Required. Provide file location in S3 and attributes to update
<details><summary>object properties</summary>

#### file_info.s3_bucket `string`
  Required. 
#### file_info.s3_object_name `string`
  Required. The file object in S3 to update.
#### file_info.robot_id `string`
  Optional. Update the robot_id associated with the file if provided.
#### file_info.robot_type `string`
  Optional. Update the robot_type associated with the file if provided.
#### file_info.robot_version `string`
  Optional. Update the robot_version associated with the file if provided.
#### file_info.metadata `string`
  Optional. Update the customized metadata
</details>

#### file `file`
Optional. New file content.
</details>

<details><summary>Example cURL</summary>

```
curl -X 'PATCH' \
  'http://localhost:9005/api/v1/file/update' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file_info={
  "s3_bucket": "files",
  "s3_object_name": "test.txt_50d3252b-80f3-4803-a30b-57784012d080",
  "robot_id": "robot02"
}'
```
</details>

### DELETE</code> <code><b>/file/delete</b></code>
Delete the file from S3 storage.  
**Note:** This API does not delete the files deployed on the robot.

<details><summary>Parameters</summary>

#### s3_bucket `string`
  Required. The bucket where the file is stored.
#### s3_object_name `string`
  Required. The object to delete.
</details>

<details><summary>Example cURL</summary>

```
curl -X 'DELETE' \
  'http://localhost:9005/api/v1/file/delete?s3_bucket=files&s3_object_name=test.txt_bdc28a7a-d504-47d9-84b8-bfc07667cea7'
```
</details>

### GET</code> <code><b>/job_state/{job_id}</b></code>
Get the deployment job state by job_id

<details><summary>Parameters</summary>

#### job_id `string`
  Required. Unique job identifier. Job id is returned by /file/deploy or /file/deploy_from_s3 API.
</details>

<details><summary>Example cURL</summary>

```
curl -X 'GET' \
  'http://127.0.0.1:9005/api/v1/job_state/bdc28a7a-d504-47d9-84b8-bfc07667cea7'
```
</details>

## Usage
### Upload Files
Use the `POST /file/upload` endpoint to upload files to S3 storage. For each file, you need to provide the file store location (s3 bucket). The API requires a list of file_info body. Here is an example:
```json
{
    "file_list": [
        {
          "s3_bucket": "files",
          "robot_id": "carter01",
          "deploy_path": "/tmp/test.txt",
          "robot_type": "carter",
          "robot_version": "v2.4",
          "file_metadata": {"type": "test"}
        }
    ]
}
```
All fields except `s3_bucket`are optional.

### List Uploaded Files
Use the `Get /file/list` endpoint to get information of files uploaded. You can provide `s3_bucket`, `s3_bucket_name`, `robot_id`, `robot_type`, `deploy_path` and `file_metadata`. The API will list all file information that meets the criterias.

### Deploy Files from Local Workstation
Use the `POST /file/deploy` endpoint to deploy a file from your workstation to a robot. The API will upload files to the S3 storage and then deploy them to the robot. The API accepts the same input as `POST /file/upload`. `robot_id` and `deploy_path` is required to indicate file destination. Here is an example:
```json
{
    "file_list": [
        {
          "s3_bucket": "files",
          "s3_object_name": "",
          "robot_id": "carter01",
          "deploy_path": "/tmp/test.txt",
          "robot_type": "carter",
          "robot_version": "v2.4",
          "file_metadata": {"type": "test"}
        }
    ]
}
```
`robot_id` should be the same as the one you set for the daemon running on the robot. The file should be deployed to `deploy_path` specified in the input body.

### Deploy a File from S3 Storage
Use the `POST /file/deploy_from_s3` endpoint to deploy an uploaded file. If `deploy_path` is not set, the file will be deployed to the path provided when it is uploaded.

### Check Deploy Job State
`/file/deploy` and `/file/deploy_from_s3` will return deployment job ids. With a job id, you can check its state using `GET /job_state/{job_id}`. 

### Delete a File
Use `DELETE /file/delete` endpoint to delete an file in S3 storage. This API does not delete files deployed on robots. `s3_bucket` and `s3_object_name` are required.
