while read line; do {
     printf 'sf -csv -z -hash sha1 -throttle 10ms -log e,w,d,s,p,t ../../Volumes/Staging/ingest/fileTransfers/%s >%ssf.csv
' $line $line
}
done <~/ft.txt> ~/sfft.sh
