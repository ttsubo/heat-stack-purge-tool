# heat-stack-purge-tool

## これは、なに？
OpenStack heatを活用してオーケストレーション制御を実現するには、適切なheat-stackを作成する必要があります。
なお、heat-stack作成時に使用されたテナントユーザが、不測の事態により、削除されてしまった場合、それ以降、当該heat-stackを削除することが大変困難になります。
このheat-stackが残留し続けると、heat-stackに関連付けられたSouthBoundリソースも残留し続けることになります。
この問題の暫定対処として、heat-stackを強制削除を実現するためのツールになります。

## どうやって使うの？
### (1) 事前準備
- テナントの登録状態を確認しておく

```
# openstack project list
+----------------------------------+---------+
| ID                               | Name    |
+----------------------------------+---------+
| 3fb0eae714da4f7d9f345641fee1f936 | demo    |
| b87b147b20a643b3a3ea29567e11f7ca | service |
| d83c0ec5ab4746988aacff093dfa9a96 | admin   |
+----------------------------------+---------+
```
- demoテナントにて作成されたheat-stackの状態を確認しておく

```
# heat --os-project-name demo stack-list
+--------------------------------------+----------------------------------------------+-----------------+---------------------+--------------+
| id                                   | stack_name                                   | stack_status    | creation_time       | updated_time |
+--------------------------------------+----------------------------------------------+-----------------+---------------------+--------------+
| d3961cf3-a6f6-4e44-b087-72b6bf9e1a8e | network_c1073b9e-6cbb-4ff8-b971-66ac840e1344 | CREATE_COMPLETE | 2019-12-01T22:04:11 | None         |
+--------------------------------------+----------------------------------------------+-----------------+---------------------+--------------+
```
- heat-stackに関連付けられたheat-resourcの状態を確認しておく

```
# heat --os-project-name demo resource-list network_c1073b9e-6cbb-4ff8-b971-66ac840e1344
+---------------+--------------------------------------+------------------------------+-----------------+---------------------+
| resource_name | physical_resource_id                 | resource_type                | resource_status | updated_time        |
+---------------+--------------------------------------+------------------------------+-----------------+---------------------+
| network       | c1073b9e-6cbb-4ff8-b971-66ac840e1344 | OS::Contrail::VirtualNetwork | CREATE_COMPLETE | 2019-12-01T22:04:11 |
+---------------+--------------------------------------+------------------------------+-----------------+---------------------+
```
- さらに、mysqlに登録されたheat-stackの状態を確認しておく

```
mysql> use contrail-heat
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
mysql> select * from stack \G;
*************************** 1. row ***************************
                   id: d3961cf3-a6f6-4e44-b087-72b6bf9e1a8e
           created_at: 2019-12-01 22:04:11
           updated_at: NULL
           deleted_at: NULL
                 name: network_c1073b9e-6cbb-4ff8-b971-66ac840e1344
      raw_template_id: 1
        user_creds_id: 1
             username: admin
             owner_id: NULL
               action: CREATE
               status: COMPLETE
        status_reason: Stack CREATE completed successfully
              timeout: 3
               tenant: 3fb0eae714da4f7d9f345641fee1f936
     disable_rollback: 1
stack_user_project_id: 3fb0eae714da4f7d9f345641fee1f936
               backup: 0
       uq_name_active: 1
         nested_depth: 0
          convergence: 0
 prev_raw_template_id: NULL
    current_traversal: NULL
         current_deps: null
 parent_resource_name: NULL
1 row in set (0.00 sec)

ERROR:
No query specified

```
- さらに、mysqlに登録されたheat-resourceの状態を確認しておく

```
mysql> select * from resource \G;
*************************** 1. row ***************************
            nova_instance: c1073b9e-6cbb-4ff8-b971-66ac840e1344
                     name: network
               created_at: 2019-12-01 22:04:11
               updated_at: NULL
                   action: CREATE
                   status: COMPLETE
            status_reason: state changed
                 stack_id: d3961cf3-a6f6-4e44-b087-72b6bf9e1a8e
            rsrc_metadata: {}
          properties_data: {"forwarding_mode": "l2_l3", "uuid": "c1073b9e-6cbb-4ff8-b971-66ac840e1344", "admin_state_up": true, "route_targets": [], "shared": false, "name": "c1073b9e-6cbb-4ff8-b971-66ac840e1344"}
                     uuid: 19c8cf58-3fb8-4ab0-9692-d546c9a988dd
                       id: 1
                engine_id: NULL
               atomic_key: NULL
                needed_by: []
                 requires: []
                 replaces: NULL
              replaced_by: NULL
      current_template_id: NULL
properties_data_encrypted: 0
            root_stack_id: d3961cf3-a6f6-4e44-b087-72b6bf9e1a8e
1 row in set (0.00 sec)

ERROR:
No query specified
```
### (2) demoテナント削除
- demoテナントを削除する

```
# openstack project delete demo
# openstack project list
+----------------------------------+---------+
| ID                               | Name    |
+----------------------------------+---------+
| b87b147b20a643b3a3ea29567e11f7ca | service |
| d83c0ec5ab4746988aacff093dfa9a96 | admin   |
+----------------------------------+---------+
```
- 再度、heat-stackの状態を確認してみる

```
# heat --os-project-name demo stack-list
The request you have made requires authentication. (HTTP 401)
```
demoテナントが既に、存在しないので、heatコマンドが失敗してしまいます


### (3) heat-stack-purge-toolを使って、heat-stackを削除する
- `purge_tool.conf`ファイルに、heat-stack削除の条件等を設定する

```
[DEFAULT]
plugin_dirs = /opt/heat/contrail-heat/contrail_heat/resources

[database]
connection = mysql://root:mysql123@mysql-heat/contrail-heat

[clients_contrail]
user = admin
password = passw0rd
tenant = admin
api_server = contrail-mock
api_port = 8082
auth_host_ip = keystone-server
client_creation_attempts = 5
client_creation_wait = 5000

[contrail]
# Contrail version: 2 or 3 is supported.
contrail_version = 3

[purge_tool]
stack_name = "network_c1073b9e-6cbb-4ff8-b971-66ac840e1344"
tenant_id = "3fb0eae714da4f7d9f345641fee1f936"
username = "demo"
```
- heat-stack-purge-toolを起動する

```
# python heat_stack_purge_tool.py
```
- purge_tool.logを確認する

```
...
2019-12-01 22:26:59,103:INFO:deleting ContrailVirtualNetwork "network" [c1073b9e-6cbb-4ff8-b971-66ac840e1344] Stack "network_c1073b9e-6cbb-4ff8-b971-66ac840e1344" [d3961cf3-a6f6-4e44-b087-72b6bf9e1a8e]
```

### (4) 事後確認
- 再度、mysqlに登録されたheat-stackの状態を確認しておく

```
mysql> select * from stack \G;
*************************** 1. row ***************************
                   id: d3961cf3-a6f6-4e44-b087-72b6bf9e1a8e
           created_at: 2019-12-01 22:04:11
           updated_at: NULL
           deleted_at: 2019-12-01 22:26:59
                 name: network_c1073b9e-6cbb-4ff8-b971-66ac840e1344
      raw_template_id: 1
        user_creds_id: 1
             username: admin
             owner_id: NULL
               action: DELETE
               status: COMPLETE
        status_reason: Stack DELETE completed successfully
              timeout: 3
               tenant: 3fb0eae714da4f7d9f345641fee1f936
     disable_rollback: 1
stack_user_project_id: 3fb0eae714da4f7d9f345641fee1f936
               backup: 0
       uq_name_active: NULL
         nested_depth: 0
          convergence: 0
 prev_raw_template_id: NULL
    current_traversal: NULL
         current_deps: null
 parent_resource_name: NULL
1 row in set (0.00 sec)

ERROR:
No query specified
```
- 再度、mysqlに登録されたheat-resourceの状態を確認しておく

```
mysql> select * from resource \G;
Empty set (0.00 sec)

ERROR:
No query specified
```


期待通りに、heat-stack, heat-resourceが削除できました ...
