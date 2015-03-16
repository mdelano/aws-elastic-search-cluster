# aws-elastic-search-cluster
Fab Script For Deploying Nodes to an AWS ElasticSearch Cluster

#### Simple Usage
```fab prod create_host:us-east-1a```

The above example creates an new ElasticSearch node in the us-east-1a availability zone. If this is the first node then it will be the master, otherwise it will discover the master and add itself to the cluster.
