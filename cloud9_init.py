"""
This script helps quickly setup a Cloud9 instance by
- Setting an auto-shutdown cloudwatch alarm
- Installing conda
- Resizing the instance 
"""

import subprocess
import sys


def set_idle_termination(idle_hours=1):
    """Set an alarm to terminate the current EC2 after `idle_hours` of idle time."""
    subprocess.run(
        f"{sys.executable} -m pip install boto3 requests", shell=True, check=True
    )
    import boto3
    import requests

    client = boto3.client("cloudwatch")
    aws_region = requests.get(
        "http://169.254.169.254/latest/meta-data/placement/region"
    ).text
    aws_account_id = boto3.client("sts").get_caller_identity().get("Account")
    aws_instance_id = requests.get(
        "http://169.254.169.254/latest/meta-data/instance-id"
    ).text
    response = client.put_metric_alarm(
        AlarmName=f"cloud9-idle-monitor-{aws_instance_id}",
        AlarmDescription="Terminate cloud9 machine when CPU is idle.",
        AlarmActions=[
            f"arn:aws:swf:{aws_region}:{aws_account_id}:action/actions/AWS_EC2.InstanceId.Terminate/1.0",
        ],
        MetricName="CPUUtilization",
        Namespace="AWS/EC2",
        Statistic="Maximum",
        Dimensions=[
            {"Name": "InstanceId", "Value": aws_instance_id},
        ],
        Period=3600,
        Unit="Percent",
        EvaluationPeriods=idle_hours,
        Threshold=2,
        ComparisonOperator="LessThanThreshold",
    )


def install_conda():
    """Downloads and install conda. Inits the conda shell for bash."""
    print(f"Installing miniconda...")
    subprocess.run(
        "wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh",
        shell=True,
        check=True,
    )
    subprocess.run("bash ~/miniconda.sh -b -p $HOME/miniconda", shell=True, check=True)
    subprocess.run(
        """eval "$($HOME/miniconda/bin/conda shell.bash hook)" 
conda init""",
        shell=True,
        check=True,
    )


def resize_instance(new_size):
    """Resize the instance to the desired size"""
    print(f"Resizing instance to {new_size} GB...")
    # From https://docs.aws.amazon.com/cloud9/latest/user-guide/move-environment.html
    RESIZE_SCRIPT = """#!/bin/bash

    # Specify the desired volume size in GiB as a command-line argument. If not specified, default to 20 GiB.
    SIZE=${1:-20}

    # Get the ID of the environment host Amazon EC2 instance.
    INSTANCEID=$(curl http://169.254.169.254/latest/meta-data/instance-id)

    # Get the ID of the Amazon EBS volume associated with the instance.
    VOLUMEID=$(aws ec2 describe-instances \
    --instance-id $INSTANCEID \
    --query "Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId" \
    --output text)

    # Resize the EBS volume.
    aws ec2 modify-volume --volume-id $VOLUMEID --size $SIZE

    # Wait for the resize to finish.
    while [ \
    "$(aws ec2 describe-volumes-modifications \
        --volume-id $VOLUMEID \
        --filters Name=modification-state,Values="optimizing","completed" \
        --query "length(VolumesModifications)"\
        --output text)" != "1" ]; do
    sleep 1
    done

    #Check if we're on an NVMe filesystem
    if [ $(readlink -f /dev/xvda) = "/dev/xvda" ]
    then
    # Rewrite the partition table so that the partition takes up all the space that it can.
    sudo growpart /dev/xvda 1

    # Expand the size of the file system.
    # Check if we are on AL2
    STR=$(cat /etc/os-release)
    SUB="VERSION_ID=\"2\""
    if [[ "$STR" == *"$SUB"* ]]
    then
        sudo xfs_growfs -d /
    else
        sudo resize2fs /dev/xvda1
    fi

    else
    # Rewrite the partition table so that the partition takes up all the space that it can.
    sudo growpart /dev/nvme0n1 1

    # Expand the size of the file system.
    # Check if we're on AL2
    STR=$(cat /etc/os-release)
    SUB="VERSION_ID=\"2\""
    if [[ "$STR" == *"$SUB"* ]]
    then
        sudo xfs_growfs -d /
    else
        sudo resize2fs /dev/nvme0n1p1
    fi
    fi
    """
    subprocess.run(RESIZE_SCRIPT, shell=True, check=True)


if __name__ == "__main__":
    disk_resize = (
        input("Do you want to resize the instance disk size ? [y/n] ")
        .lower()
        .startswith("y")
    )
    if disk_resize:
        new_size = input("Which size do you want to resize to, in GB? ")
        resize_instance(new_size)
    conda_install = (
        input("Do you want to install miniconda ? [y/n] ").lower().startswith("y")
    )
    if conda_install:
        install_conda()
    set_idle_alarm = (
        input("Do you want to set an auto-shutdown based on CPU ? [y/n] ")
        .lower()
        .startswith("y")
    )
    if set_idle_alarm:
        set_idle_termination()
    print(f"Done with init_script.")
