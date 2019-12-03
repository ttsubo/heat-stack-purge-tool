# heat-stack-purge-tool for heat-juno

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
| 1baba4bc10444cada4023c02bd1f114c | admin   |
| d45be0f05d9748f491db9e49fb230eab | demo    |
| d727e035945d450f98ee4a5e633e7b1b | service |
+----------------------------------+---------+
```
- demoテナントにて作成されたheat-stackの状態を確認しておく

```
# heat --os-project-name demo stack-list
+--------------------------------------+----------------------------------------------+-----------------+----------------------+
| id                                   | stack_name                                   | stack_status    | creation_time        |
+--------------------------------------+----------------------------------------------+-----------------+----------------------+
| 428ab810-5946-42c0-b18b-042d312de06f | network_811d15de-b1f2-465d-9020-2f6d40313017 | CREATE_COMPLETE | 2019-12-03T00:22:47Z |
+--------------------------------------+----------------------------------------------+-----------------+----------------------+
```
- heat-stackに関連付けられたheat-resourcの状態を確認しておく

```
# heat --os-project-name demo resource-list network_811d15de-b1f2-465d-9020-2f6d40313017
+---------------+--------------------------------------+------------------------------+-----------------+----------------------+
| resource_name | physical_resource_id                 | resource_type                | resource_status | updated_time         |
+---------------+--------------------------------------+------------------------------+-----------------+----------------------+
| network       | 811d15de-b1f2-465d-9020-2f6d40313017 | OS::Contrail::VirtualNetwork | CREATE_COMPLETE | 2019-12-03T00:22:47Z |
+---------------+--------------------------------------+------------------------------+-----------------+----------------------+
```
- さらに、mysqlに登録されたheat-stackの状態を確認しておく

```
mysql> use contrail-heat
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
mysql> select * from stack \G;
*************************** 1. row ***************************
                   id: 428ab810-5946-42c0-b18b-042d312de06f
           created_at: 2019-12-03 00:22:47
           updated_at: NULL
                 name: network_811d15de-b1f2-465d-9020-2f6d40313017
      raw_template_id: 12
        user_creds_id: 10
             username: admin
             owner_id: NULL
               status: COMPLETE
        status_reason: Stack CREATE completed successfully
           parameters: {"parameters": {"admin_state_up": true, "uuid": "811d15de-b1f2-465d-9020-2f6d40313017", "name": "811d15de-b1f2-465d-9020-2f6d40313017"}, "resource_registry": {"resources": {}}}
              timeout: 3
               tenant: d45be0f05d9748f491db9e49fb230eab
     disable_rollback: 1
               action: CREATE
           deleted_at: NULL
stack_user_project_id: d45be0f05d9748f491db9e49fb230eab
               backup: 0
       uq_name_active: 1
1 row in set (0.00 sec)

ERROR:
No query specified

```
- さらに、mysqlに登録されたheat-resourceの状態を確認しておく

```
mysql> select * from resource \G;
*************************** 1. row ***************************
             id: 75403a37-893f-43da-b881-89f26b9d66d5
  nova_instance: 811d15de-b1f2-465d-9020-2f6d40313017
           name: network
     created_at: 2019-12-03 00:22:47
     updated_at: NULL
         status: COMPLETE
  status_reason: state changed
       stack_id: 428ab810-5946-42c0-b18b-042d312de06f
  rsrc_metadata: {}
         action: CREATE
properties_data: {"forwarding_mode": "l2_l3", "uuid": "811d15de-b1f2-465d-9020-2f6d40313017", "admin_state_up": true, "shared": false, "route_targets": [], "name": "811d15de-b1f2-465d-9020-2f6d40313017"}
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
| 1baba4bc10444cada4023c02bd1f114c | admin   |
| d727e035945d450f98ee4a5e633e7b1b | service |
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
stack_name = "network_811d15de-b1f2-465d-9020-2f6d40313017"
tenant_id = "d45be0f05d9748f491db9e49fb230eab"
username = "demo"
```
- heat-stack-purge-toolを起動する

```
# python heat_stack_purge_tool.py
...
Stack DELETE COMPLETE (network_811d15de-b1f2-465d-9020-2f6d40313017): Stack DELETE completed successfully
```
- purge_tool.logを確認する

```
...
2019-12-03 00:37:21,179:INFO:Stack DELETE IN_PROGRESS (network_811d15de-b1f2-465d-9020-2f6d40313017): Stack DELETE started
2019-12-03 00:37:21,195:INFO:deleting ContrailVirtualNetwork "network" [811d15de-b1f2-465d-9020-2f6d40313017] Stack "network_811d15de-b1f2-465d-9020-2f6d40313017" [428ab810-5946-42c0-b18b-042d312de06f]
2019-12-03 00:37:22,631:INFO:Stack DELETE COMPLETE (network_811d15de-b1f2-465d-9020-2f6d40313017): Stack DELETE completed successfully
```

### (4) 事後確認
- 再度、mysqlに登録されたheat-stackの状態を確認しておく

```
mysql> select * from stack \G;
*************************** 1. row ***************************
                   id: 428ab810-5946-42c0-b18b-042d312de06f
           created_at: 2019-12-03 00:22:47
           updated_at: NULL
                 name: network_811d15de-b1f2-465d-9020-2f6d40313017
      raw_template_id: 12
        user_creds_id: 10
             username: admin
             owner_id: NULL
               status: COMPLETE
        status_reason: Stack DELETE completed successfully
           parameters: {"parameters": {"admin_state_up": true, "uuid": "811d15de-b1f2-465d-9020-2f6d40313017", "name": "811d15de-b1f2-465d-9020-2f6d40313017"}, "resource_registry": {"resources": {}}}
              timeout: 3
               tenant: d45be0f05d9748f491db9e49fb230eab
     disable_rollback: 1
               action: DELETE
           deleted_at: 2019-12-03 00:37:22
stack_user_project_id: d45be0f05d9748f491db9e49fb230eab
               backup: 0
       uq_name_active: NULL
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
