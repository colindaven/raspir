#!/bin/bash

## Marie-Madlen Pust
## Last updated: 27 January 2021
## pust.marie-madlen@mh-hannover.de   ### Remove this to avoid this being scraped for SPAM -- contact via github is better !

# set partition
#SBATCH -p normal

# set run on x MB node only
#SBATCH --mem 30000

# set run x cpus
#SBATCH --cpus-per-task 8

# set name of job
#SBATCH --job-name=raspir_prepare

# Add miniconda3 to PATH
. /mnt/ngsnfs/tools/miniconda3/etc/profile.d/conda.sh

# Activate env on cluster node
conda activate raspir_env >> /dev/null

cpus=8
human_chr_pattern="1_1_1"

# Only run SAM section if SAM files exist in the current directory
count=`ls -1 *.sam 2>/dev/null | wc -l`
if [ $count != 0 ]
    then
    # run SAM conversion

	# For pipelines which start from SAM. Many pipelines will start from BAM.
	for items in *.sam
		do
			echo $items
			fname=$(echo ${items} | sed 's/.sam//')
			echo $fname


			# Remove reads with low mapping quality
			samtools view -hM -q 20 $items > ${items%.sam}.mq20.sam

			# Convert file from SAM to BAM format
			samtools view -h -b -S ${items%.sam}.mq20.sam  > ${fname}.bam

			# Discard unmapped sequences @Marie are these not removed by the mq20 filter, I think so ?
			samtools view -b -F 4 $items > ${fname}_1.bam

			# Sort bam file
			samtools sort @ $cpus -${fname}_1.bam -o ${fname}.sorted.bam
		done
fi

# Start from sorted mq20 BAM with no unmapped sequences  
for items in *.bam
	do
		echo $items
		fname=$(echo ${items} | sed 's/.bam//')
		echo $fname

   		# Obtain coverage information
   		#samtools depth ${fname}.sorted.bam > ${fname}.sorted.raspir1.csv
   		samtools depth ${fname}.bam | grep -v $human_chr_pattern  > ${fname}.raspir1.csv

   		# Add genome size
		   ### COLIN TODO - items here is for SAM format , sed fails on bam
   		samtools view -H ${items} | sed 's/LN://g' > ${fname}.genomeSize_1.csv
   		sed -i 's/SN://g' ${fname}.genomeSize_1.csv
   		cut -f2- ${fname}.genomeSize_1.csv > ${fname}.genomeSize.csv

   		# Add column with genome size
   		#awk -v FS="\t" -v OFS="\t" 'FNR==NR{a[$1]=$2;next;} {if(a[$1]) {print a[$1], $0} else {print "NA",$0}}' ${fname}.genomeSize.csv ${fname}.raspir1.csv > ${fname}.raspir.csv
		awk -v FS="\t" -v OFS="\t" 'FNR==NR{a[$1]=$2;next;} {if(a[$1]) {print a[$1], $0} else {print "NA",$0}}' \
		${fname}.genomeSize.csv ${fname}.raspir1.csv > ${fname}.raspir.csv

		# Convert into a comma-separated file
		sed -i 's/\t/,/g' ${fname}.raspir.csv
		# Add header
		sed -i '1iGenomeLength,Organism,Position,Depth\' ${fname}.raspir.csv

		# Remove intermediate files
		#rm ${fname}.raspir1.csv ${fname}.genomeSize_1.csv ${fname}.genomeSize.csv
	done
