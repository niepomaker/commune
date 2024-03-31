#!/bin/bash

# Prompt User for variables
echo "Enter your vali name. Do not include 'vali::' "
read VALI_NAME
echo "Enter your host ip. Do not include 'http://'"
read HOST
echo "Enter your host port "
read PORT
echo "Enter your key name for staking the validator. Requires 277"
read KEY
echo "What subnet would you like to deploy it on? Must be a valid integer"
read SUBNET
echo "What should the delegation rate be? 1-100"
read DELEGATION_FEE

# Confirm configuration is correct
echo "This is your validator configuration: "
echo $VALI_NAME
echo $HOST
echo $PORT
echo $KEY
echo $SUBNET
echo $DELEGATION_FEE
echo "Is this correct? (y/n)"
read ANSWER
if [ "$ANSWER" != "y" ]; then
    exit 1
fi

# Serve the validator module
echo "Serving vali"
comx module serve vali\:\:$VALI_NAME $HOST_IP $PORT $KEY —netuid=$SUBNET
exit_value $?
if [ $? -ne 0 ]; then
    exit 1
    else
    # Prompt user to continue before spending com
    echo "Successfully served vali. The next step will cost 227com. Continue? (y/n)"
    read ANSWER
    if [ "$ANSWER" != "y" ]; then
        echo "User canceled. Exiting"
        exit 1
    fi
fi

# Register the validator
echo "Registering vali"
comx module register vali\:\:$VALI_NAME $HOST_IP $PORT $KEY --netuid=$SUBNET
exit_value $?
if [ $? -ne 0 ]; then
    echo "Failed to register vali. Exiting"
    exit 1
fi

# Change the delegation fee
echo "Changing Delegation Fee"
comx module update module vali\:\:$VALI_NAME $HOST_IP $PORT --delegation-fee $DELEGATION_FEE
exit_value $?
if [ $? -ne 0 ]; then
    echo "Failed to change delegation fee. Exiting"
    exit 1
fi

# Start the voting loop
echo "Starting voteloop"
c voteloop vali\:\:$VALI_NAME
exit_value $?
if [ $? -ne 0 ]; then
    echo "Failed to start voteloop. Exiting"
    exit 1
fi

# Deploy the vali
echo "Vali has been deployed. It is ready to be used."
exit 0