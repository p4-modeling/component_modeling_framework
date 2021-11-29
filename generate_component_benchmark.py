#!/usr/bin/env python3

import os
import argparse
import logging as log
import pathlib
import glob
import yaml
from pprint import pformat

from framework.specification import generate as generate_specification
from framework.experiment import generate as generate_experiment


BASEPATH = pathlib.Path(__file__).parent.absolute()


TARGETS = [
    # 'p4_bmv2',
    'p4_t4p4s',
    'p4_nfp',
    # 'p4_netfpga',
    # 'p4_tofino',
    # 'linux',
    # 'vpp'
]

TESTBEDS = [
    'pos',
    'manual'
]

LOG_FORMAT = '[%(levelname)s] %(message)s'


def argument_parser():
    parser = argparse.ArgumentParser('Generate experiment configuration for benchmarking a component')
    parser.add_argument('target', type=str, choices=TARGETS,
                        help='the device target')
    parser.add_argument('testbed', type=str, choices=TESTBEDS,
                        help='the testbed environment')
    parser.add_argument('outdir',
                        help='output directory, experiment ID will be appended')

    # options
    parser.add_argument('--test-nodes', metavar='LG_DUT', type=str,
                        choices=[os.path.splitext(name.split('/')[-1])[0]
                                 for name in glob.glob(os.path.join(BASEPATH, 'node_config/*.yml'))],
                        help='configuration regarding the pair of nodes for this experiment (node_config/LG_DUT.yml)')
    parser.add_argument('--max-load-repetitions', type=int, default=3,
                        help='repetitions of max load measurement')
    # TODO metrics

    # ### different components
    subparsers = parser.add_subparsers(help='available program components', dest='component')
    # baseline
    parser_base = subparsers.add_parser('baseline', help='baseline (default)')
    group_base = parser_base.add_mutually_exclusive_group(required=True)
    group_base.add_argument('--load', default=False, action='store_true',
                            help='scale load on dut')
    group_base.add_argument('--cpu-frequency', default=False, action='store_true',
                            help='scale cpu frequency')
    # MAT
    parser_mat = subparsers.add_parser('mat', help='match-action tables')
    group_mat = parser_mat.add_mutually_exclusive_group(required=True)
    group_mat.add_argument('--number-of-entries-exact', default=False, action='store_true',
                           help='scale number of table entries')
    group_mat.add_argument('--number-of-entries-ternary', default=False, action='store_true',
                           help='scale number of ternary table entries')
    group_mat.add_argument('--number-of-entries-lpm', default=False, action='store_true',
                           help='scale number of lpm table entries')
    group_mat.add_argument('--key-width', default=False, action='store_true',
                           help='scale key width')
    group_mat.add_argument('--number-of-tables-exact', default=False, action='store_true',
                            help='scale number of tables')
    group_mat.add_argument('--number-of-same-tables-exact', default=False, action='store_true',
                            help='scale number of repeated table applies')
    group_mat.add_argument('--number-of-tables-lpm', default=False, action='store_true',
                            help='scale number of LPM tables')
    group_mat.add_argument('--number-of-tables-ternary', default=False, action='store_true',
                            help='scale number of ternary tables')
    group_mat.add_argument('--number-action-data', default=False, action='store_true',
                           help='scale number of action data entries')
    group_mat.add_argument('--number-of-match-keys-exact', default=False, action='store_true',
                            help='scale number of exact match keys')
    group_mat.add_argument('--number-of-match-keys-ternary', default=False, action='store_true',
                            help='scale number of ternary match keys')
    # parser
    parser_parse = subparsers.add_parser('parser', help='parser')
    group_parse = parser_parse.add_mutually_exclusive_group(required=True)
    group_parse.add_argument('--number-of-parsed-fields', default=False, action='store_true',
                             help='scale number of parsed header fields')
    group_parse.add_argument('--added-headers', default=False, action='store_true',
                             help='scale number of added headers')
    group_parse.add_argument('--removed-headers', default=False, action='store_true',
                             help='scale number of removed headers')
    group_parse.add_argument('--added-headers-size', default=False, action='store_true',
                             help='scale number of added headers of different size')
    # other
    parser_other = subparsers.add_parser('other', help='other processing')
    group_other = parser_other.add_mutually_exclusive_group(required=True)
    group_other.add_argument('--number-of-header-field-writes', default=False, action='store_true',
                             help='scale number of header field writes')
    group_other.add_argument('--number-of-meta-field-writes', default=False, action='store_true',
                             help='scale number of meta field writes')
    return parser.parse_args()


def main():
    args = argument_parser()

    if not args.component:
        args.component = 'baseline'

    # logger
    log.basicConfig(
        level=log.DEBUG,
        format=LOG_FORMAT
    )

    # load node config
    with open(os.path.join(BASEPATH, 'node_config', args.test_nodes + '.yml')) as fh:
        args.node_config = yaml.safe_load(fh.read())

    ## gather configs
    spec = generate_specification(args)
    log.info(pformat(spec))

    ## create files
    generate_experiment(spec)

    log.info('Done')


if __name__ == '__main__':
    main()
