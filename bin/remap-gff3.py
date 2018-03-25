#! /usr/bin/env python
# Contributed by Li-Mei Chiang <dytk2134 [at] gmail [dot] com> (2018)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
import os
import subprocess
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    lh = logging.StreamHandler()
    lh.setFormatter(logging.Formatter('%(levelname)-8s %(message)s'))
    logger.addHandler(lh)

__version__ = '1.0'

def tmp_identifier(in_gff, out_gff):
    import uuid
    out_f = open(out_gff, 'w')
    with open(in_gff, 'rb') as in_f:
        for line in in_f:
            line = line.strip()
            if len(line) != 0:
                if not line.startswith('#'):
                    tokens = line.split('\t')
                    attributes = dict(re.findall('([^=;]+)=([^=;\n]+)', tokens[8]))
                    # add tmp_identifier attribute to feature in gff3 file
                    temp_id = str(uuid.uuid1())
                    attributes['tmp_identifier'] = temp_id
                    attributes_list = list()
                    for key in attributes:
                        attributes_list.append('%s=%s' % (str(key), str(attributes[key])))
                    # update cloumn 9
                    tokens[8] = ';'.join(attributes_list)
                    out_f.write('\t'.join(tokens) + '\n')
                else:
                    out_f.write(line + '\n')

def remove_tmpID(in_gff, out_gff):
    out_f = open(out_gff, 'w')
    with open(in_gff, 'rb') as in_f:
        for line in in_f:
            line = line.strip()
            if len(line) != 0:
                if not line.startswith('#'):
                    tokens = line.split('\t')
                    attributes = dict(re.findall('([^=;]+)=([^=;\n]+)', tokens[8]))
                    del attributes['tmp_identifier']
                    attributes_list = list()
                    for key in attributes:
                        attributes_list.append('%s=%s' % (str(key), str(attributes[key])))
                    # update cloumn 9
                    tokens[8] = ';'.join(attributes_list)
                    out_f.write('\t'.join(tokens) + '\n')
                else:
                    out_f.write(line + '\n')

def filter_not_exact_match(CrossMap_mapped_file, CrossMap_log_file, filtered_file,tmp_identifier):
    not_exact_match = set()
    with open(CrossMap_log_file, 'rb') as log:
        for line in log:
            line = line.strip()
            if len(line) != 0:
                if line[0] != '#':
                    token = line.split("\t")
                    if len(token) < 10:
                        continue
                    match_state = token[9]
                    if 'not exact match' in match_state:
                        attribute_dict = dict(re.findall('([^=;]+)=([^=;\n]+)', token[8]))
                        if tmp_identifier:
                            if 'tmp_identifier' in attribute_dict:
                                not_exact_match.add(attribute_dict['tmp_identifier'])
                        else:
                            if 'ID' in attribute_dict:
                                not_exact_match.add(attribute_dict['ID'])
                            else:
                                logger.error('All features should have ID attributes. Please run the command with -tmp_ID.')
    out_f = open(filtered_file, 'w')
    with open(CrossMap_mapped_file, 'rb') as in_f:
        for line in in_f:
            line = line.strip()
            if len(line) != 0:
                if line[0] != '#':
                    token = line.split("\t")
                    if len(token) != 9:
                        continue
                    else:
                        attribute_dict = dict(re.findall('([^=;]+)=([^=;\n]+)', token[8]))
                        if tmp_identifier:
                            if 'tmp_identifier' in attribute_dict and attribute_dict['tmp_identifier'] not in not_exact_match:
                                out_f.write(line + '\n')
                        else:
                            if 'ID' in attribute_dict and attribute_dict['ID'] not in not_exact_match:
                                out_f.write(line + '\n')
    out_f.close()  
    
    
if __name__ == '__main__':
    import argparse
    from textwrap import dedent
    import re_construct_gff3_features
    import get_remove_feature
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=dedent("""\

    Quick start:
    python %(progs)s -a alignment.gff3 -t_fa target.fa -q_fa query.fa -g A.gff3 B.gff3 C.gff3
    """))

    parser.add_argument('-a', '--alignment_file', type=str, help='NCBI\'s whole-genome alignments(gff3 format).', required=True)
    parser.add_argument('-t_fa', '--target_fasta', type=str, help='Target genome assembly', required=True)
    parser.add_argument('-q_fa', '--query_fasta', type=str, help='Query genome assembly', required=True)
    parser.add_argument('-g', '--input_gff', nargs='+', type=str, help='List one or more GFF3 files to be updated.', required=True)
    parser.add_argument('-tmp_ID', '--tmp_identifier', action="store_true", help='Generate a unique temporary identifier for all the feature in the input gff3 files. (Default: False)', default=False)
    parser.add_argument('-chain', '--chain_file', type=str, help='Input a ready-made chain file.')
    parser.add_argument('-tmp', '--temp', action="store_false", help='Store all the intermediate files/temporary files into [alignment_filename]_tmp/ directory. (Default: False)')
    parser.add_argument('-u', '--updated_postfix', default='_updated', help='The filename postfix for updated features (default: "_updated")')
    parser.add_argument('-r', '--removed_postfix', default='_removed', help='The filename postfix for removed features (default: "_removed")')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)

    args = parser.parse_args()

    temp_dir = '_'.join([os.path.splitext(args.alignment_file)[0], 'tmp'])
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    chain_file = None
    if not args.chain_file:
        import gff3_to_chain
        # generate a chain file and store in the [alignment_filename]_tmp/ directory
        chain_file = '%s.%s' % (os.path.splitext(args.alignment_file)[0], 'chain')
        logger.info('Generate a chain file: (%s)', chain_file)
        gff3_to_chain.main(alignment_file=args.alignment_file, target=args.target_fasta, query=args.query_fasta, output=chain_file)
    else:
        chain_file = args.chain_file
    
    for gff3 in args.input_gff:
        gff3_filename, gff3_extension = os.path.splitext(os.path.basename(gff3))
        in_gff = gff      
        if args.tmp_identifier:
            # add tmp_identifier attribute to all the features in the input gff3 files
            out_gff = '%s/%s_%s.%s' % (temp_dir, gff3_filename, 'mod', gff3_extension)
            tmp_identifier(in_gff, out_gff)
            out_gff = in_gff
        # run CrossMap
        CrossMap_mapped_file = '%s/%s_CrossMap%s' % (temp_dir, gff3_filename, gff3_extension)
        CrossMap_log_file = '%s/%s_CrossMap%s' % (temp_dir, gff3_filename, 'log')
        subprocess.Popen(['CrossMap.py', 'gff', chain_file, in_gff3, CrossMap_mapped_file).wait()
        subprocess.Popen(['CrossMap.py', 'gff', chain_file, in_gff3, '>', CrossMap_log_file).wait()
        # remove all the not exact match features from the CrossMap output
        filtered_file = '%s/%s_CrossMap_filtered%s' % (temp_dir, gff3_filename, gff3_extension)
        filter_not_exact_match(CrossMap_mapped_file, CrossMap_log_file, filtered_file, args.tmp_identifier)
        # re-construct the parent features
        re_construct_file = '%s/%s_re_construct%s' % (temp_dir, gff3_filename, gff3_extension)
        re_construct_report = '%s/%s_re_construct%s' % (temp_dir, gff3_filename, '.report')
        re_construct_gff3_features.main(in_gff, filtered_file, re_construct_file, re_construct_report, args.tmp_identifier)
        # run gff3_QC to generate QC report for re-constructed gff3 file
        re_construct_QC = '%s/%s_re_construct_QC.report' % (temp_dir, gff3_filename)
        subprocess.Popen(['gff3_QC.py', '-g', re_construct_file, '-f', args.query_fasta, '-o', re_construct_QC]).wait()
        # remove all the incorrectly merged gene parents (Ema0009) and incorrectly split parents (Emr0002) from QC report
        re_construct_QC_filtered = '%s/%s_re_construct_QC_filtered.report' % (temp_dir, gff3_filename)
        subprocess.Popen(['grep', '-v' ,'\'Emr0002\'', re_construct_QC, '|', 'grep', '-v', '\'Ema0009\'', '>', re_construct_QC_filtered]).wait()
        # run gff3_fix
        update_gff = '%s%s%s' % (os.path.splitext(gff3), args.updated_postfix, gff3_extension)
        remove_gff = '%s%s%s' % (os.path.splitext(gff3), args.removed_postfix, gff3_extension)
        update_gff_QC = '%s_QC%s' % (os.path.splitext(gff3), gff3_extension)
        if args.tmp_identifier:
            tmp_update_gff = '%s/%s%s_tmp%s' % (temp_dir, in_gff3, args.updated_postfix, gff3_extension)
            subprocess.Popen(['gff3_fix.py', '-qc_r', re_construct_QC_filtered, '-g', re_construct_file, '-og', tmp_update_gff])
            get_remove_feature.output_remove_features(in_gff, tmp_update_gff, remove_gff, tmp_identifier)
            remove_tmpID(tmp_update_gff, update_gff)
        else:
            subprocess.Popen(['gff3_fix.py', '-qc_r', re_construct_QC_filtered, '-g', re_construct_file, '-og', update_gff])
            get_remove_feature.output_remove_features(in_gff, update_gff, remove_gff, tmp_identifier)
        subprocess.Popen(['gff3_QC.py', '-g', update_gff, '-f', args.query_fasta, '-o', update_gff_QC]).wait()

        







    