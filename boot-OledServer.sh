#!/bin/sh
# (c) 2018 Yoichi Tanibayashi
#
MYNAME=`basename $0`

BINDIR=${HOME}/bin
LOGDIR=${HOME}/tmp
ENVDIR=${HOME}/env
ENVBIN=${ENVDIR}/bin
LOGFILE=${LOGDIR}/${MYNAME}.log

CMDNAME="OledServer.py"
CMD=${BINDIR}/${CMDNAME}

if [ -x ${ENVBIN}/${CMDNAME} ]; then
    CMD=${ENVBIN}/${CMDNAME}
fi

if [ ! -d ${LOGDIR} ]; then
    mkdir ${LOGDIR}
fi

if [ -f ${ENVBIN}/activate ]; then
    . ${ENVBIN}/activate
fi

date > ${LOGFILE} 2>&1
${CMD} >> ${LOGFILE} 2>&1
