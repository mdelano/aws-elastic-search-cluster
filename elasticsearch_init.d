#!/bin/bash
# elasticsearch daemon
# chkconfig: 345 20 80
# description: elasticsearch daemon
# processname: elasticsearch

DAEMON_PATH="/usr/local/elasticsearch/elasticsearch-1.4.4/bin"

DAEMON=elasticsearch
DAEMONOPTS="-Xmx2g -Xms2g"

NAME=elasticsearch
DESC="ElasticSearch DB Instance"
PIDFILE=/var/run/$NAME.pid
SCRIPTNAME=/etc/init.d/$NAME

case "$1" in
start)
	printf "Starting..."
	PID=`${DAEMON_PATH}/${DAEMON} ${DAEMONOPTS} > /dev/null 2>&1 & echo $!`
	#echo "Saving PID" $PID " to " $PIDFILE
        if [ -z $PID ]; then
            printf "Fail"
        else
            echo $PID > $PIDFILE
            printf "Ok"
        fi
;;
status)
        printf "Checking"
        if [ -f $PIDFILE ]; then
            PID=`cat $PIDFILE`
            if [ -z "`ps axf | grep ${PID} | grep -v grep`" ]; then
                printf "Process dead but pidfile exists"
            else
                echo "Running"
            fi
        else
            printf "Service not running"
        fi
;;
stop)
        printf "Stopping "
            PID=`cat $PIDFILE`
            cd $DAEMON_PATH
        if [ -f $PIDFILE ]; then
            kill -HUP $PID
            printf "Ok"
            rm -f $PIDFILE
        else
            printf "pidfile not found"
        fi
;;

restart)
  	$0 stop
  	$0 start
;;

*)
        echo "Usage: $0 {status|start|stop|restart}"
        exit 1
esac
