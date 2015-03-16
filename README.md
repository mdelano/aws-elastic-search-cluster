# aws-elastic-search-cluster
Fab Script For Deploying Nodes to an AWS ElasticSearch Cluster

#### Simple Usage
```fab prod create_host:us-east-1a```

The above example creates an new ElasticSearch node in the us-east-1a availability zone. If this is the first node then it will be the master, otherwise it will discover the master and add itself to the cluster.

#### Examples
##### Create a new node in a specific cluster
```fab create_host:cluster_name=Thor```
##### Create a new node with a specific instance type
```fab create_host:instance_type=c3.large```
##### Create a new node with a specific AMI
```fab create_host:ami='ami-427a392a'```
##### Spread your nodes accross availability zones
```fab create_host:ec2_placement='us-east-1a'```
##### Group your nodes by environment
```fab create_host:environment='dev'```
