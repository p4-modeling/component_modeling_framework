'''
functions for generating an experiment specification
'''
import sys
import os
import logging as log


def _get_table_scaling():
    tens = range(8)
    each = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    # each = [1, 1.25, 1.5, 1.75, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5]
    scale = []
    for ten in tens:
        for e in each:
            if ten == 7 and e > 2:
                break
            value = int((10 ** ten) * e)
            if value not in scale:
                scale.append(value)
    return scale


def _get_default_program_args():
    return {
        'baseline': False,
        'number_header_fields': 1,
        'header_field_size': 8,
        'number_match_keys': 1,
        'repeat_apply_tables': 1,
        'number_tables': 1,
        'number_table_apply': 1,
        'number_table_entries': 0,
        'action_data': 0,
        'match_key_size': 8,
        'match_type': 'exact',
        'skip_filling_tables': False,
        'no_emit': False,
        'add_uninteresting_header': False,
        'default_action': None,
        'action': None,
        'deparser_add_headers': 0,
        'deparser_remove_headers': 0,
        'deparser_add_headers_size': 1,
        'header_field_writes': 0,
        'meta_field_writes': 0,
        'match_last': False,
    }


def generate(args):
    log.info('Generate specification')
    spec = {}

    ### meta
    spec['meta'] = {
        'testbed': args.testbed
    }

    ### metrics
    spec['metrics'] = {}

    # what is of interest
    # TODO make configurable from CLI
    m = ['throughput', 'packet_rate', 'latency']
    if args.target == 'p4_t4p4s':
        m.append('cpu_load')
        m.append('cache_misses')

        perf_stat = {
            'r08d1': 'L1_cache_misses',
            'r10d1': 'L2_cache_misses',
            'r20d1': 'L3_cache_misses',
            'cycles': 'CPU_cycles',
        }
        spec['metrics']['perf'] = perf_stat
    elif args.target == 'p4_nfp':
        m.append('resources')
    spec['metrics']['names'] = m

    # what should scale for the experiment series
    s = {}
    if args.target == 'p4_t4p4s':
        # for software targets we can scale cpu cores
        s['cpu_cores'] = [1, 2, 3, 4] + [len(args.node_config['dut']['cores'])]
    spec['metrics']['scale'] = s

    ### traffic
    t = {}
    t['pattern'] = 'cbr'
    t['load'] = {
        'max': '10', # in gbit/s
        'latency': [0.1, 0.5, 0.7], # percentages of max load
    }
    t['packet_size'] = [64, 128, 256, 512, 1024, 1500]
    t['payload_u32_offset'] = 0
    if isinstance(t['packet_size'], list):
        # add also to scaling variables
        spec['metrics']['scale']['packet_size'] = t['packet_size']
    spec['traffic'] = t
    # content of packets will be defined by concrete test

    # program, will be defined later
    spec['program'] = {
        'architecture': 'v1model',
        'args': _get_default_program_args(),
        'scale': None
    }
    if args.target == 'p4_t4p4s':
        spec['program']['target'] = 't4p4s'

    ## model
    spec['model'] = {
        'x_axis': None,
        'plot_per': ['packet_size'],
        'log_scale': False,
        'model_max_parts': 1,
        'model_start': 0,
        'model_end': 0,
        'convert_to_cycles': False,
    }
    if args.target == 'p4_t4p4s' and 'cpu_load' in spec['metrics']['names']:
        spec['model']['convert_to_cycles'] = max(args.node_config['dut']['cpu_frequencies'])

    outdir = [args.outdir, args.component]
    experiment_name = None

    if args.component == 'baseline':
        log.info('Baseline program')
        if args.load:
            log.info('Scaling load')
            experiment_name = 'load_rate'
            x_axis = 'load_rate'
            spec['metrics']['scale'][x_axis] = [round(0.01 * i, 2) for i in range(1, 11)]
            spec['model']['model_end'] = 1 # 100% load makes no sense to model
        elif args.cpu_frequency:
            log.info('Scaling cpu frequency')
            experiment_name = 'cpu_frequency'
            x_axis = 'cpu_frequency'
            #spec['metrics']['scale']['cpu_cores'] = [1, 2]
            spec['metrics']['scale']['cpu_frequency'] = args.node_config['dut']['cpu_frequencies']
            spec['model']['convert_to_cycles'] = 'from_loop'
        else:
            log.error('Feature not yet supported')
            sys.exit(5)
        spec['program']['args']['baseline'] = True
    elif args.component == 'mat':
        log.info('Match action tables')
        if args.number_of_entries_exact:
            log.info('Scaling number of exact table entries')
            experiment_name = 'number_entries_exact'
            x_axis = 'table_entries'
            spec['metrics']['scale'][x_axis] = _get_table_scaling()
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'exact'
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_table_entries',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                spec['model']['model_max_parts'] = 5
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_of_entries_ternary:
            log.info('Scaling number of ternary table entries')
            experiment_name = 'number_entries_ternary'
            x_axis = 'table_entries'
            spec['metrics']['scale'][x_axis] = _get_table_scaling()
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'ternary'
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_table_entries',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                spec['model']['model_max_parts'] = 5
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_of_entries_lpm:
            log.info('Scaling number of lpm table entries')
            experiment_name = 'number_entries_lpm'
            x_axis = 'table_entries'
            spec['metrics']['scale'][x_axis] = _get_table_scaling()
            #spec['metrics']['scale'][x_axis] = [1, 100, 1000, 10000, 100000]
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'lpm'
            spec['program']['args']['number_match_keys'] = 1
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_table_entries',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                spec['model']['model_max_parts'] = 5
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
                # more detailed evaluation of DIR-24-8 structure
                #spec['metrics']['scale'][x_axis] = [x + 256 for x in _get_table_scaling()] # with 32 bit entries
        elif args.number_of_tables_exact:
            log.info('Scaling number of exact tables')
            experiment_name = 'tables'
            x_axis = 'tables'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 6, 8, 10, 16, 20, 32, 50, 64, 100, 128, 150, 200, 256, 300, 400, 512, 700, 900, 1024]
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'exact'
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_tables',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_of_tables_lpm:
            log.info('Scaling number of LPM tables')
            experiment_name = 'tables_lpm'
            x_axis = 'tables'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 6, 8, 10, 16, 20, 32, 50, 64, 100, 128, 150, 200, 256, 300, 400, 512, 700, 900, 1024]
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'lpm'
            spec['program']['args']['number_match_keys'] = 1
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_tables',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_of_tables_ternary:
            log.info('Scaling number of ternary tables')
            experiment_name = 'tables_ternary'
            x_axis = 'tables'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 6, 8, 10, 16, 20, 32, 50, 64, 100, 128, 150, 200, 256, 300, 400, 512, 700, 900, 1024]
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'ternary'
            spec['program']['args']['number_table_entries'] = 1
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_tables',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_of_same_tables_exact:
            log.info('Scaling number of same exact table applies')
            experiment_name = 'tables_repeat'
            x_axis = 'tables'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 6, 8, 10, 16, 20, 32, 64, 128, 256, 512, 1024]
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'exact'
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_table_apply',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_action_data:
            log.info('Scaling number of action data')
            experiment_name = 'number_action_data'
            x_axis = 'action_data'
            spec['metrics']['scale'][x_axis] = [1, 2, 4, 8, 10, 20, 40, 80, 100, 200, 400, 800, 1000, 2000]
            spec['model']['log_scale'] = True

            # program
            spec['program']['args']['match_type'] = 'exact'
            spec['program']['args']['match_key_size'] = 32
            spec['program']['args']['add_uninteresting_header'] = True
            spec['program']['args']['action'] = 'scale_action_data'
            spec['program']['args']['default_action'] = 'drop'
            spec['program']['args']['number_header_fields'] = 1
            spec['program']['args']['header_field_size'] = 32
            # individual programs
            spec['program']['scale'] = {
                'arg': 'action_data',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # to speed up inserting table entries
                spec['program']['args']['skip_filling_tables'] = True
        elif args.number_of_match_keys_exact:
            log.info('Scaling number of exact match keys')
            experiment_name = 'match_keys'
            x_axis = 'match_keys'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 6, 8, 10, 16, 20, 32, 50, 64, 100, 128, 150, 200, 256, 470]
            spec['metrics']['scale']['packet_size'] = [512]

            # program
            spec['program']['args']['match_type'] = 'exact'
            spec['program']['args']['match_key_size'] = 8
            spec['program']['args']['header_field_size'] = 8
            spec['program']['args']['number_header_fields'] = 470
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_match_keys',
                'with': x_axis
            }
        elif args.number_of_match_keys_ternary:
            log.info('Scaling number of ternary match keys')
            experiment_name = 'match_keys'
            x_axis = 'match_keys'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 6, 8, 10, 16, 20, 32, 50, 64, 100, 128, 150, 200, 256, 470]
            spec['metrics']['scale']['packet_size'] = [512]

            # program
            spec['program']['args']['match_type'] = 'ternary'
            spec['program']['args']['match_key_size'] = 8
            spec['program']['args']['header_field_size'] = 8
            spec['program']['args']['number_header_fields'] = 470
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_match_keys',
                'with': x_axis
            }
        else:
            log.error('Feature not yet supported')
            sys.exit(5)
    elif args.component == 'parser':
        log.info('Parser')
        if args.added_headers:
            log.info('Scaling number of added headers')
            experiment_name = 'added_headers'
            x_axis = 'add_headers'
            spec['metrics']['scale'][x_axis] = list(range(0, 10)) + \
                                               list(range(10, 150, 10))

            # need fixed-size large packets
            spec['traffic']['packet_size'] = 300
            if 'packet_size' in spec['metrics']['scale']:
                spec['metrics']['scale']['packet_size'] = 300

            # individual programs
            spec['program']['scale'] = {
                'arg': 'deparser_add_headers',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # DPDK can only add ~120 bytes, exclude anything else in model
                spec['model']['model_end'] = len([x for x in spec['metrics']['scale'][x_axis] if x > 120])
                # do not model for 0 added headers
                spec['model']['model_start'] = 1
                # to add extra complexity
                spec['program']['args']['repeat_apply_tables'] = 4
        elif args.removed_headers:
            log.info('Scaling number of removed headers')
            experiment_name = 'removed_headers'
            x_axis = 'remove_headers'
            spec['metrics']['scale'][x_axis] = list(range(0, 10)) + \
                                               list(range(10, 150, 10))

            # need fixed-size large packets
            spec['traffic']['packet_size'] = 300
            if 'packet_size' in spec['metrics']['scale']:
                spec['metrics']['scale']['packet_size'] = 300

            # individual programs
            spec['program']['scale'] = {
                'arg': 'deparser_remove_headers',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                ## DPDK can only remove ~120 bytes, exclude anything else in model
                spec['model']['model_end'] = len([x for x in spec['metrics']['scale'][x_axis] if x > 110])
                # do not model for 0 removed headers
                spec['model']['model_start'] = 1
                # to add extra complexity
                spec['program']['args']['repeat_apply_tables'] = 6
        elif args.added_headers_size:
            log.info('Scaling size of added headers')
            experiment_name = 'added_headers_size'
            x_axis = 'add_headers_size'
            spec['metrics']['scale'][x_axis] = list(range(1, 10)) + \
                                               list(range(10, 150, 10))

            # need fixed-size large packets
            spec['traffic']['packet_size'] = 300
            if 'packet_size' in spec['metrics']['scale']:
                spec['metrics']['scale']['packet_size'] = 300

            # program
            spec['program']['args']['deparser_add_headers'] = 1
            # individual programs
            spec['program']['scale'] = {
                'arg': 'deparser_add_headers_size',
                'with': x_axis
            }

            if args.target == 'p4_t4p4s':
                # DPDK can only add ~120 bytes, exclude anything else in model
                spec['model']['model_end'] = len([x for x in spec['metrics']['scale'][x_axis] if x > 120])
                # to add extra complexity
                spec['program']['args']['repeat_apply_tables'] = 4
        elif args.number_of_parsed_fields:
            log.info('Scaling number of parsed header fields')
            experiment_name = 'number_parsed_fields'
            x_axis = 'parsed_fields'
            spec['metrics']['scale'][x_axis] = [1, 2, 3, 4, 5, 8, 10, 16, 32]
            number_tables = 1

            # manual switch for even more fields with larger packet size
            extended = True
            if extended:
                spec['metrics']['scale'][x_axis] = [0, 1, 2, 4, 6, 8, 10, 12, 16, 20, 25, 32, 40, 50, 64, 80, 100, 128, 150, 200, 256, 300, 350, 400, 470]
                spec['metrics']['scale']['packet_size'] = [512]
                number_tables = 2

            # program
            spec['program']['args']['header_field_size'] = 8
            spec['program']['args']['match_key_size'] = 8
            spec['program']['args']['number_tables'] = number_tables
            spec['program']['args']['match_last'] = False
            # individual programs
            spec['program']['scale'] = {
                'arg': 'number_header_fields',
                'with': x_axis + 4
            }
        else:
            log.error('Feature not yet supported')
            sys.exit(5)
    elif args.component == 'other':
        log.info('Other processing')
        if args.number_of_header_field_writes:
            log.info('Scaling number of header field writes')
            experiment_name = 'header_field_writes'
            x_axis = 'header_field_writes'
            spec['metrics']['scale'][x_axis] = [0, 1, 2, 3, 4, 5, 8, 10, 16, 32, 40]

            # manual switch for even more fields with larger packet size
            extended = True
            if extended:
                spec['metrics']['scale'][x_axis] = [0, 1, 2, 4, 8, 16, 32, 64, 128, 200, 256, 350, 470]
                spec['metrics']['scale']['packet_size'] = [512, 1024, 1500]

            # program
            spec['program']['args']['header_field_size'] = 8
            spec['program']['args']['match_key_size'] = 8
            spec['program']['args']['number_header_fields'] = max(spec['metrics']['scale'][x_axis])
            # individual programs
            spec['program']['scale'] = {
                'arg': 'header_field_writes',
                'with': x_axis
            }
        elif args.number_of_meta_field_writes:
            log.info('Scaling number of meta field writes')
            experiment_name = 'meta_field_writes'
            x_axis = 'meta_field_writes'
            spec['metrics']['scale'][x_axis] = [0, 1, 2, 4, 8, 16, 32, 64, 128, 200, 256, 350, 470]
            #spec['metrics']['scale'][x_axis] = [1, 2, 4, 8, 16, 32, 50, 64, 100, 128, 150, 200, 256, 300, 350, 400, 450, 512, 750, 1024, 1500, 2048, 3000, 4096, 5000, 6000]

            # program
            spec['program']['args']['header_field_size'] = 8
            spec['program']['args']['match_key_size'] = 8
            # individual programs
            spec['program']['scale'] = {
                'arg': 'meta_field_writes',
                'with': x_axis
            }
        else:
            log.error('Feature not yet supported')
            sys.exit(5)
    else:
        log.error('Component not yet supported')
        sys.exit(2)

    outdir.append(experiment_name)
    outdir = os.path.join(*outdir)

    spec['meta']['target'] = args.target
    spec['meta']['component'] = args.component
    spec['meta']['feature'] = experiment_name
    spec['meta']['outdir'] = outdir
    spec['meta']['max_load_repetitions'] = args.max_load_repetitions

    spec['model']['x_axis'] = x_axis
    spec['node_config'] = args.node_config
    return spec
