#!python
import os
from fabric.api import *
from fabric.contrib import *
from fabric.contrib.files import *
from fabric.operations import run, put
from fabric.colors import red, green, yellow, cyan, magenta
import boto
import boto.ec2.elb
import boto.utils
import time

# remove -l because otherwise sudo -u looks for the invoking user's .bash_profile
env.shell = "/bin/bash -c"
#env.use_ssh_config = True
env.forward_agent = True
env.application_tag = "elasticsearch"
env.user = "ubuntu"
env.key_filename = ["~/.ssh/production.pem"]

# additional constants
environment_tag_name = "Environment"
application_tag_name = "Application"
cluster_tag_name = "ElasticSearchCluster"
ec2_region = 'us-east-1'
ec2_availability_zone = ec2_region + 'a'
ami = 'ami-427a392a'

def info(message):
    return cyan('(%s) %s' % (env.host, message))


def yay(message):
    return green('(%s) %s' % (env.host, message))


def boo(message):
    return red('(%s) %s' % (env.host, message))


def prod():
    env.env = "prod"
    env.environment_tag = "prod"
    env.papertrail_group = "783143"
    env.instance_type = 'c3.large'
    env.cluster = "Thor"
    env.elb_name = "elasticsearch-cluster-prod"


def cluster():
    print cyan('finding instances in Application=') + magenta(env.application_tag) + cyan(' Environment=') + \
        magenta(env.environment_tag)
    ec2 = boto.ec2.connect_to_region(ec2_region)
    reservations = ec2.get_all_instances(filters={
        "tag:"+environment_tag_name: env.environment_tag,
        "tag:"+application_tag_name: env.application_tag,
        'instance-state-name': 'running'})
    hostlist = []

    for reservation in reservations:
        for instance in reservation.instances:
            print "instance %s %s %s" % (yellow(instance.id), instance.public_dns_name, cyan(instance.state))
            hostlist.append(str(instance.public_dns_name))
    if len(hostlist) > 0:
        print green("found %d instances running in Application=%s Environment=%s" %
                    (len(hostlist), env.application_tag, env.environment_tag))
    else:
        print red("no running instances found in Application=%s Environment=%s" %
                  (env.application_tag, env.environment_tag))
    env.hosts = hostlist


def find_instance(instance_id):
    instance = None
    ec2 = boto.ec2.connect_to_region(ec2_region)
    reservations = ec2.get_all_instances(filters={
        "tag:"+environment_tag_name: env.environment_tag,
        "tag:"+application_tag_name: env.application_tag})
    for reservation in reservations:
        for eachInstance in reservation.instances:
            if eachInstance.id == instance_id:
                instance = eachInstance
                break
    if instance is None:
        print red("instance %s not found in Application=%s Environment=%s" % (env.application_tag, env.environment_tag))
    else:
        print "instance %s %s %s" % (yellow(instance.id), instance.public_dns_name, cyan(instance.state))
        env.hosts = [instance.public_dns_name]

def create_host(placement=ec2_availability_zone):
    print cyan("creating a new host and deploying")
    ec2 = boto.ec2.connect_to_region(ec2_region)
    reservation = ec2.run_instances(
        ami,
        key_name='production',
        instance_type=env.instance_type,
        security_groups=['production'],
        placement=placement)
    instance = reservation.instances[0]

    status = instance.update()
    while status == 'pending':
        print cyan("waiting for instance %s to start, public dns name [%s]" % (instance.id, instance.public_dns_name))
        time.sleep(10)
        status = instance.update()

    if status == 'running':
        print cyan("tagging newly created instance")
        instance.add_tag(environment_tag_name, env.environment_tag)
        instance.add_tag(application_tag_name, env.application_tag)
        instance.add_tag(cluster_tag_name, env.cluster)
        instance.add_tag("Name", env.application_tag+" "+env.environment_tag)
        env.host_string = instance.public_dns_name

        volume = ec2.create_volume(100, placement, snapshot=None, volume_type='gp2', iops=None, encrypted=False, dry_run=False)
        status = ''
        while status != 'available':
            status = ec2.get_all_volumes([volume.id])[0].status
            print "Volume status: %s" % status
            time.sleep(1)

        volume.attach(instance.id, '/dev/sdh')
        volume.add_tag(environment_tag_name, env.environment_tag)
        volume.add_tag(application_tag_name, env.application_tag)
        volume.add_tag(cluster_tag_name, env.cluster)
        volume.add_tag("Name", env.application_tag+" "+env.environment_tag)

        status = instance.update()
        print cyan("Status:" + status)
        while status == 'pending':
            print cyan("waiting for instance %s to start, public dns name [%s]" % (instance.id, instance.public_dns_name))
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
    setup_host()

def setup_host():
    sudo('mkdir /mnt2')
    sudo('sudo mkfs -t ext4 /dev/xvdh')
    sudo('mount -t ext4 /dev/xvdh /mnt2')
    install_sun_java()
    sudo('apt-get install -y -q unzip')
    sudo('wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.4.zip')
    sudo('unzip elasticsearch-1.4.4 -d /usr/local/elasticsearch')
    sudo('rm elasticsearch-1.4.4.zip')
    with cd('/usr/local/elasticsearch/elasticsearch-1.4.4/'):
        sudo('bin/plugin install elasticsearch/elasticsearch-cloud-aws/2.4.1')
        sudo('bin/plugin -i elasticsearch/marvel/latest')

    configure()

    # CopperEgg
    sudo('curl -sk http://uTwRdkAYClguDmFC@api.copperegg.com/rc.sh | sh')

    sudo('/usr/local/elasticsearch/elasticsearch-1.4.4/bin/elasticsearch -d', pty=False)
    print yay('host setup complete')

def install_sun_java():
    print info('installing java')
    sudo('apt-get -y install software-properties-common')
    sudo('apt-add-repository -y ppa:webupd8team/java')
    sudo('apt-get -y update')
    sudo('echo debconf shared/accepted-oracle-license-v1-1 select true |  debconf-set-selections')
    sudo('echo debconf shared/accepted-oracle-license-v1-1 seen true |  debconf-set-selections')
    sudo('DEBIAN_FRONTEND=noninteractive apt-get -y install oracle-java7-installer')

def configure():
    ####
    ##### Use the key from the elasticsearch IAM user #####
    ####
    env.AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
    env.AWS_ACCESS_SECRET = os.environ['AWS_ACCESS_SECRET']
    env.CLUSTER_TAG_NAME = cluster_tag_name

    source_file = './elasticsearch.yml'
    destination_file = 'elasticsearch.yml'
    upload_template(source_file, destination_file, context=env, mode=0644)
    sudo('cp ~/elasticsearch.yml /usr/local/elasticsearch/elasticsearch-1.4.4/config/elasticsearch.yml')
