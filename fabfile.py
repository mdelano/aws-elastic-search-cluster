#!python
import os
import time
import datetime
from fabric.api import *
from fabric.contrib import *
from fabric.contrib.files import *
from fabric.operations import run, put
from fabric.colors import red, green, yellow, cyan, magenta
import boto
import boto.ec2.elb
import boto.utils
import time





# Set Fabric environment vars
env.shell               = "/bin/bash -c" # remove -l because otherwise sudo -u looks for the invoking user's .bash_profile
env.forward_agent       = True
env.user                = "ubuntu"
env.key_filename        = ["~/.ssh/production.pem"]





# Constants to support the creation of the ElasticSearch cluster at EC2
CLUSTER_TAG_NAME        = "ElasticSearchCluster"
ENVIRONMENT_TAG_NAME    = "Environment"
APPLICATION_TAG_NAME    = "Application"
APPLICATION             = "elasticsearch"




# Console logging helpers
def info(message):
    return cyan('(%s) %s' % (env.host, message))


def yay(message):
    return green('(%s) %s' % (env.host, message))


def boo(message):
    return red('(%s) %s' % (env.host, message))




################################################################
#
# Creates a new ElasticSearch node
#
# ami: The target EC2 instance image
# instance_type:    http://aws.amazon.com/ec2/instance-types/
# ec2_region:       http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
# ec2_placement:    http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html
# environment:      This can be any environment identifier. I use dev, beta, prod, etc
# cluster_name:     ElasticSeearch clusters have a name. Think of a good one.
#
################################################################
def create_host(ami='ami-427a392a', instance_type='c3.large', ec2_region='us-east-1', ec2_placement='us-east-1a', environment='dev', cluster_name='elasticsearch', from_snapshot=None):
    env.CLUSTER_NAME = cluster_name
    env.ENVIRONMENT = environment

    print cyan("Creating a new ElasticSearch node for cluster %s" % (env.CLUSTER_NAME))

    # Spin up the instance
    ec2 = boto.ec2.connect_to_region(ec2_region)
    reservation = ec2.run_instances(
        ami,
        key_name='production',
        instance_type=instance_type,
        security_groups=['ElasticSearch-SecurityGroup-Prod'],
        placement=ec2_placement)
    instance = reservation.instances[0]

    # Wait for the instance to come online
    status = instance.update()
    while status == 'pending':
        print cyan("waiting for instance %s to start, public dns name [%s]" % (instance.id, instance.public_dns_name))
        time.sleep(10)
        status = instance.update()

    # Tag the instance so we can find it later
    if status == 'running':
        print cyan("tagging newly created instance")
        instance.add_tag(ENVIRONMENT_TAG_NAME, environment)
        instance.add_tag(APPLICATION_TAG_NAME, APPLICATION)
        instance.add_tag(CLUSTER_TAG_NAME, env.CLUSTER_NAME)
        instance.add_tag("Name", APPLICATION+" "+ environment)
        env.host_string = instance.public_dns_name

        # Create and attach an EBS volume to the new instance
        volume = ec2.create_volume(200, ec2_placement, snapshot=None, volume_type='gp2', iops=None, encrypted=False, dry_run=False)
        status = ''
        while status != 'available':
            status = ec2.get_all_volumes([volume.id])[0].status
            print "Volume status: %s" % status
            time.sleep(1)

        volume.attach(instance.id, '/dev/sdh')
        volume.add_tag(ENVIRONMENT_TAG_NAME, environment)
        volume.add_tag(APPLICATION_TAG_NAME, APPLICATION)
        volume.add_tag(CLUSTER_TAG_NAME, env.CLUSTER_NAME)
        volume.add_tag("Name", APPLICATION+" "+environment)

        # Confirm that the instance is ready after attaching the new volume
        status = instance.update()
        print cyan("Status:" + status)
        while status == 'pending':
            print cyan("waiting for instance %s to be ready, public dns name [%s]" % (instance.id, instance.public_dns_name))
            time.sleep(10)
            status = instance.update()
    else:
        print red('launched instance status: ' + status)
        raise RuntimeError("unable to launch new host")

    # Now that the status is running, it's not yet launched. The only way to tell if it's fully up is to try to SSH in.
    if status == "running":
        retry = True
        while retry:
            try:
                run('true')
                retry = False
            except:
                print cyan("waiting for instance %s to open ssh, public dns name %s" %
                           (instance.id, instance.public_dns_name))
                time.sleep(10)
    print green("instance %s created, public dns name %s" % (instance.id, instance.public_dns_name))

    # Build out the new instance
    setup_host()

    if(from_snapshot is not None):
        time.sleep(10)
        restore(s3_bucket='elasticsearch.backups.mediasilo.com',snapshot_name=from_snapshot)



################################################################
#
# Build out an ElasticSearch node
#
################################################################
def setup_host():
    # Attach our new EBS volume
    sudo('mkdir /mnt2')
    sudo('sudo mkfs -t ext4 /dev/xvdh')
    sudo('mount -t ext4 /dev/xvdh /mnt2')

    install_sun_java()

    sudo('apt-get install -y -q unzip')

    # Install ElasticSearch
    sudo('wget http://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.4.zip')
    sudo('unzip elasticsearch-1.4.4 -d /usr/local/elasticsearch')
    sudo('rm elasticsearch-1.4.4.zip')

    # Setup ElasticSearch to run as a daemon
    source_file = './elasticsearch_init.d'
    destination_file = 'elasticsearch'
    upload_template(source_file, destination_file, context=env, mode=0644)
    sudo('cp ~/elasticsearch /etc/init.d/elasticsearch')
    sudo('chmod 777 /etc/init.d/elasticsearch')

    # elasticsearch.yml
    configure()

    with cd('/usr/local/elasticsearch/elasticsearch-1.4.4/'):
        # Install ElasticSearch plugins
        sudo('bin/plugin install elasticsearch/elasticsearch-cloud-aws/2.4.1')

    # CopperEgg
    sudo('curl -sk http://uTwRdkAYClguDmFC@api.copperegg.com/rc.sh | sh')

    # Start ElasticSearch
    sudo('service elasticsearch start', pty=False)

    print yay('host setup complete')




################################################################
#
# This is an ElasticSearch dependency.
# We call this method as a part of the host setup
#
################################################################
def install_sun_java():
    print info('installing java')
    sudo('apt-get -y install software-properties-common')
    sudo('apt-add-repository -y ppa:webupd8team/java')
    sudo('apt-get -y update')
    sudo('echo debconf shared/accepted-oracle-license-v1-1 select true |  debconf-set-selections')
    sudo('echo debconf shared/accepted-oracle-license-v1-1 seen true |  debconf-set-selections')
    sudo('DEBIAN_FRONTEND=noninteractive apt-get -y install oracle-java7-installer')




################################################################
#
# Send the ElasticSearch config file to the target node(s)
# in the cluster
#
# The credentials below should be for an IAM user with both S3
# and EC2 permissions.
#
# Here is an example S3 policy that will work:
#
#{
#    "Statement": [
#        {
#            "Action": [
#                "s3:ListBucket"
#            ],
#            "Effect": "Allow",
#            "Resource": [
#                "arn:aws:s3:::elasticsearch.backups.mediasilo.com"
#            ]
#        },
#        {
#            "Action": [
#                "s3:GetObject",
#                "s3:PutObject",
#                "s3:DeleteObject"
#            ],
#            "Effect": "Allow",
#            "Resource": [
#                "arn:aws:s3:::elasticsearch.backups.mediasilo.com/*"
#            ]
#        }
#    ],
#    "Version": "2012-10-17"
#}
#
# Here is an example EC2 policy that will work:
#{
#    "Version": "2012-10-17",
#    "Statement": [
#        {
#            "Sid": "Stmt1426206108000",
#            "Effect": "Allow",
#            "Action": [
#                "ec2:AttachVolume",
#                "ec2:CopySnapshot",
#                "ec2:CreateImage",
#                "ec2:CreateSnapshot",
#                "ec2:CreateVolume",
#                "ec2:CopyImage",
#                "ec2:DeleteSnapshot",
#                "ec2:DeleteVolume",
#                "ec2:DescribeAvailabilityZones",
#                "ec2:DescribeImageAttribute",
#                "ec2:DescribeImages",
#                "ec2:DescribeInstanceAttribute",
#                "ec2:DescribeInstanceStatus",
#                "ec2:DescribeInstances",
#                "ec2:DescribeRegions",
#                "ec2:DescribeReservedInstances",
#                "ec2:DescribeSnapshotAttribute",
#                "ec2:DescribeSnapshots",
#                "ec2:DescribeSpotInstanceRequests",
#                "ec2:DescribeSecurityGroups",
#                "ec2:DescribeTags",
#                "ec2:DescribeVolumeAttribute",
#                "ec2:DescribeVolumeStatus",
#                "ec2:DescribeVolumes",
#                "ec2:DetachVolume",
#                "ec2:EnableVolumeIO",
#                "ec2:ImportVolume",
#                "ec2:ModifyVolumeAttribute"
#            ],
#            "Resource": [
#                "*"
#            ]
#        }
#    ]
#}
#
################################################################
def configure(instance_id=None, environment='dev', ec2_region='us-east-1'):
    if instance_id is None:
        cluster(environment, ec2_region)
    else:
        find_instance(instance_id, environment, ec2_region)

    ##### Use the key from the elasticsearch IAM user #####
    env.AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
    env.AWS_ACCESS_SECRET = os.environ['AWS_ACCESS_SECRET']
    env.CLUSTER_TAG_NAME = CLUSTER_TAG_NAME

    source_file = './elasticsearch.yml'
    destination_file = 'elasticsearch.yml'
    upload_template(source_file, destination_file, context=env, mode=0644)
    sudo('cp ~/elasticsearch.yml /usr/local/elasticsearch/elasticsearch-1.4.4/config/elasticsearch.yml')





def snapshot(s3_bucket, environment='dev', ec2_region='us-east-1'):
    create_snapshot_repository_cmd = "curl -XPUT 'localhost:9200/_snapshot/"+CLUSTER_TAG_NAME+"_snapshot_repository' -d '{\"type\": \"s3\",\"settings\": {\"bucket\": \""+s3_bucket+"\",\"region\": \""+ec2_region+"\"}}'"
    d = datetime.datetime.now()
    create_snapshot_cmd = "curl -XPUT \"localhost:9200/_snapshot/"+CLUSTER_TAG_NAME+"_snapshot_repository/"+d.strftime('%m_%d_%y_%I-%M-%S%p').lower()+"\""

    hosts = get_cluster_instances(environment, ec2_region)
    with settings(host_string=hosts[0]):
        run(create_snapshot_repository_cmd)
        run(create_snapshot_cmd)




def restore(s3_bucket, snapshot_name, ec2_region='us-east-1'):
    create_snapshot_repository_cmd = "curl -XPUT 'localhost:9200/_snapshot/"+CLUSTER_TAG_NAME+"_snapshot_repository' -d '{\"type\": \"s3\",\"settings\": {\"bucket\": \""+s3_bucket+"\",\"region\": \""+ec2_region+"\"}}'"
    restore_snapshot_cmd = "curl -XPOST \"localhost:9200/_snapshot/"+CLUSTER_TAG_NAME+"_snapshot_repository/"+snapshot_name+"/_restore\""

    print info("Restoring snapshot " + snapshot_name + " from " + s3_bucket)
    sudo(create_snapshot_repository_cmd)
    sudo(restore_snapshot_cmd)


################################################################
#
# Set the hosts list for all nodes in the ElasticSearch cluster.
# This tells fabric what hosts to run against.

# See http://docs.fabfile.org/en/latest/usage/execution.html
# for more info on the Fabric execution model
#
################################################################
def cluster(environment='dev', ec2_region='us-east-1'):
    env.hosts = get_cluster_instances(environment, ec2_region)



################################################################
#
# Set the hosts from the first found node in the ElasticSearch cluster.
# This tells fabric what hosts to run against.

# See http://docs.fabfile.org/en/latest/usage/execution.html
# for more info on the Fabric execution model
#
################################################################
def any(environment='dev', ec2_region='us-east-1'):
    hosts = get_cluster_instances(environment, ec2_region)
    env.hosts = hosts[0]




################################################################
#
# Finds all nodes in the cluster
#
################################################################
def get_cluster_instances(environment='dev', ec2_region='us-east-1'):
    print cyan('finding instances in Application=') + magenta(APPLICATION) + cyan(' Environment=') + \
        magenta(environment)
    ec2 = boto.ec2.connect_to_region(ec2_region)
    reservations = ec2.get_all_instances(filters={
        "tag:"+ENVIRONMENT_TAG_NAME: environment,
        "tag:"+APPLICATION_TAG_NAME: APPLICATION,
        'instance-state-name': 'running'})
    hostlist = []

    for reservation in reservations:
        for instance in reservation.instances:
            print "instance %s %s %s" % (yellow(instance.id), instance.public_dns_name, cyan(instance.state))
            hostlist.append(str(instance.public_dns_name))
    if len(hostlist) > 0:
        print green("found %d instances running in Application=%s Environment=%s" %
                    (len(hostlist), APPLICATION, environment))
    else:
        print red("no running instances found in Application=%s Environment=%s" %
                  (APPLICATION, environment))

    return hostlist





################################################################
#
# Set the hosts list from a specific node in the ElasticSearch cluster.
# This tells fabric what hosts to run against.

# See http://docs.fabfile.org/en/latest/usage/execution.html
# for more info on the Fabric execution model
#
################################################################
def find_instance(instance_id=None, environment='dev', ec2_region='us-east-1'):
    instance = None
    ec2 = boto.ec2.connect_to_region(ec2_region)
    reservations = ec2.get_all_instances(filters={
        "tag:"+ENVIRONMENT_TAG_NAME: environment,
        "tag:"+APPLICATION_TAG_NAME: APPLICATION})
    for reservation in reservations:
        for eachInstance in reservation.instances:
            if eachInstance.id == instance_id:
                instance = eachInstance
                break
    if instance is None:
        print red("instance %s not found in Application=%s Environment=%s" % (APPLICATION, environment))
    else:
        print "instance %s %s %s" % (yellow(instance.id), instance.public_dns_name, cyan(instance.state))
        env.hosts = [instance.public_dns_name]
