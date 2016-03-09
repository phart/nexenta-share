#!/bin/bash
#
# loop over a csv to do shares with share.py script
#
# usage: do_shares.sh csvfilename.csv
#   expects simple comma separated file, no quotes, no spaces
#
SERVER=127.0.0.1
PORT=8457
CREDS="YWRtaW46bmV4ZW50YQ=="

if [ "$#" -eq 0 ]; then
    echo usage: $0 csvfilename.csv
    exit 1
fi

while read LINE
do
    IFS=',' read -r -a list <<< "$LINE"
    if [ "${list[2]}" == "nfs" ]; then
        echo ./share.py -s $SERVER -P $PORT -e $CREDS -n "${list[0]}" "${list[1]}"
        ./share.py -s $SERVER -P $PORT -e $CREDS -n "${list[0]}" "${list[1]}"
    elif [ "${list[2]}" == "cifs" ]; then
        echo ./share.py -s $SERVER -P $PORT -e $CREDS -c "${list[3]}" "${list[0]}" "${list[1]}" 
        ./share.py -s $SERVER -P $PORT -e $CREDS -c "${list[3]}" "${list[0]}" "${list[1]}" 
    else
        echo for share "${list[0]}", "${list[2]}" is not a valid value for the third field of the CSV file
        exit 1
    fi
done < $1
