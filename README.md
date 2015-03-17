# aws-elastic-search-cluster
Fab Script For Deploying Nodes to an AWS ElasticSearch Cluster

#### Simple Usage
```$ fab prod create_host:us-east-1a```

The above example creates an new ElasticSearch node in the us-east-1a availability zone. If this is the first node then it will be the master, otherwise it will discover the master and add itself to the cluster.

#### Installation
There are 3 required dependencies: [Python](https://www.python.org/downloads/), [Paramiko](http://paramiko-www.readthedocs.org/en/latest/installing.html), and [Boto](https://github.com/boto/boto#installation)
##### Install [Fabric](http://www.fabfile.org/installing.html)
```$ pip install fabric```
```$ pip install paramiko```

##### Install [Boto](https://github.com/boto/boto#installation)
```$ pip install boto```

##### [Configure Boto](http://docs.pythonboto.org/en/latest/boto_config_tut.html) by saving you AWS key and secret to ~/.boto
```
[Credentials]
aws_access_key_id = <your_access_key_here>
aws_secret_access_key = <your_secret_key_here>
```

#### Examples
##### Create a new node in a specific cluster
```$ fab create_host:cluster_name=Thor```
##### Create a new node with a specific instance type
```$ fab create_host:instance_type=c3.large```
##### Create a new node with a specific AMI
```$ fab create_host:ami='ami-427a392a'```
##### Spread your nodes accross availability zones
```$ fab create_host:ec2_placement='us-east-1a'```
##### Group your nodes by environment
```$ fab create_host:environment='dev'```

#### Monitoring
When the instance is setup the Marvel plugin is installed so keeping an eye on your cluster is easy. On any node in your cluster got to http://HOST:9200/_plugin/marvel

#### Snapshot and Restore
Prior to taking a snapshot you must first create an s3 bucket to which the snapshot will be persisted. This bucket is the first parameter of the snapshot example that follows. Additionally, you need to have a valid [IAM policy](https://github.com/elastic/elasticsearch-cloud-aws#recommended-s3-permissions) before running a snapshot. You snapshot will be saved as mm_dd_yyyy_hh_mm_ss\[am|pm\] (eg. 03_16_2015_01-59-01pm)
##### Take a snapshot 
```$ fab snapshot:'my.s3.snapshot.bucket',environment='dev',ec2_region='us-east-1'```

You can create a new cluster from an existing snapshot. It must be the first node in the cluster.
##### Iniitialize cluster from a snapshot
```$ fab create_host:cluster_name=Thor,from_snapshot=03_16_2015_01-59-01pm```
