'''
generate the experiment based on a specification
'''


import os
import sys
import logging as log
import subprocess
import pathlib
import yaml
import glob
import shutil
import json
from jinja2 import Environment, select_autoescape, FileSystemLoader
from string import Template


BASEPATH = os.path.join(pathlib.Path(__file__).parent.absolute(), '..')
TEMPLATES = os.path.join(BASEPATH, 'templates')


DIRS = {
    'experiment': 'experiment',
    'evaluation': 'evaluation',
    'data': 'data',
    'dut': 'experiment/dut',
    'dut_config': 'experiment/dut/config',
    'lg': 'experiment/lg',
    'lg_script': 'experiment/lg/measurement_scripts',
    'lg_util': 'experiment/lg/util_scripts',
}


LG = 'lg'
DUT = 'dut'


JINJA = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(default=True)
)

JINJA_C = Environment(
    loader=FileSystemLoader(TEMPLATES),
    autoescape=select_autoescape(default=True),
    block_start_string='@@',
    block_end_string='@@',
    variable_start_string='@=',
    variable_end_string='=@'
)


class NotebookTemplate(Template):
    delimiter = '#$'


def dump_specification(spec):
    log.info('Dumping specification')
    dumped = yaml.dump(spec)
    target = os.path.join(spec['meta']['outdir'], 'specification.yml')
    with open(target, 'w') as outfile:
        outfile.write(dumped)


def generate_loop_variables(spec):
    log.info('Generating loop variables')
    dumped = yaml.dump(spec['metrics']['scale'])
    target = os.path.join(spec['meta']['outdir'], DIRS['experiment'], 'loop-variables.yml')
    with open(target, 'w') as outfile:
        outfile.write(dumped)


def copy_tree_evaluation(src, dst):
    blacklist = [
        'sample_data',
        'venv3',
        'figures',
        'data',
        'build'
    ]
    if not os.path.exists(dst):
        os.makedirs(dst)
    for file in glob.glob(src + '/*', recursive=True) + [src + '/.gitignore']:
        if any([block in file for block in blacklist]):
            continue
        subprocess.run(['cp', '-r', file, dst])


def generate_evaluation(spec):
    log.info('Copying evaluation scripts')
    subdir = 'deps/plot_scripts'
    src = os.path.join(BASEPATH, subdir)
    dst = os.path.join(spec['meta']['outdir'], DIRS['evaluation'])

    copy_tree_evaluation(src, dst)
    try:
        shutil.rmtree(os.path.join(dst, 'util', '__pycache__'))
    except FileNotFoundError:
        pass

    log.info('Inserting evaluation configuration')
    m = spec['model']
    config = {
        'result_dir_file': os.path.realpath(os.path.join(spec['meta']['outdir'], 'result_directory.txt')),
        'loop_x_axis': m['x_axis'],
        'loop_plot_per': m['plot_per'],
        'loadgen': spec['node_config']['loadgen']['name'],
        'dut': spec['node_config']['dut']['name'],
        'target': spec['meta']['target'],
        'experiment_name': spec['meta']['feature'],
        'latency_rates': ['rate'] if spec['meta']['feature'] == 'load_rate' else [],
        'log_scale': 'True' if m['log_scale'] else '',
        'convert_to_cycles': m['convert_to_cycles'] if m['convert_to_cycles'] else '',
        'repetitions': spec['meta']['max_load_repetitions'],
        'model_parts': [i for i in range(1, m['model_max_parts'] + 1)],
        'model_start': m['model_start'],
        'model_end': m['model_end'],
        'only_core_id': spec['node_config']['moongen_core_id'],
        'perf_stat_events':  [(event, name) for event, name in spec['metrics']['perf'].items()],
    }
    templated = 'configuration = {}'.format(json.dumps(config)).replace('"', "'")
    for filename in [os.path.join(spec['meta']['outdir'], DIRS['evaluation'], 'plot_throughput.ipynb'),
                     os.path.join(spec['meta']['outdir'], DIRS['evaluation'], 'plot_throughput.py'),
                     os.path.join(spec['meta']['outdir'], DIRS['evaluation'], 'plot_latency.ipynb'),
                     os.path.join(spec['meta']['outdir'], DIRS['evaluation'], 'plot_latency.py'),
                     os.path.join(spec['meta']['outdir'], DIRS['evaluation'], 'plot_perf_stat.ipynb'),
                     os.path.join(spec['meta']['outdir'], DIRS['evaluation'], 'plot_perf_stat.py')]:
        with open(filename, 'r+') as fh:
            content = fh.read()
            template = NotebookTemplate(content)
            finished = template.substitute(configuration=templated)
            fh.seek(0)
            fh.write(finished)
    files = [
        {
            'template': 'run.sh',
            'to': os.path.join(DIRS['evaluation'], 'run_evaluation.sh')
        }, {
            'template': 'setup.sh',
            'to': os.path.join(DIRS['evaluation'], 'setup_evaluation.sh')
        }, {
            'template': 'compress_data.sh',
            'to': os.path.join(DIRS['evaluation'], 'compress_data.sh'),
            'variables': {
                'data_dir': DIRS['data']
            }
        }, {
            'template': 'setup_node.sh',
            'to': os.path.join(DIRS['evaluation'], 'setup_node.sh')
        }
    ]
    copy_templates_to_experiment(files, 'evaluation', spec['meta']['outdir'])


def generate_p4_planes(spec, suffix=None,
                       baseline=False,
                       number_header_fields=1,
                       header_field_size=8,
                       number_match_keys=1,
                       repeat_apply_tables=1,
                       number_tables=1,
                       number_table_apply=1,
                       number_table_entries=0,
                       action_data=0,
                       match_key_size=8,
                       match_type='exact',
                       skip_filling_tables=False,
                       no_emit=False,
                       add_uninteresting_header=False,
                       default_action=None,
                       action=None,
                       deparser_add_headers=0,
                       deparser_remove_headers=0,
                       deparser_add_headers_size=1,
                       header_field_writes=0,
                       meta_field_writes=0,
                       match_last=False,
                       ):
    log.info('Generating P4 data and control plane')
    dut_config_path = DIRS['dut_config']
    if suffix:
        dut_config_path = os.path.join(dut_config_path, suffix)
    outdir = os.path.join(spec['meta']['outdir'], dut_config_path)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    dummy_ethernet = True
    if baseline:
        dummy_ethernet = False
        number_header_fields = 1
        header_field_size = 8
        number_match_keys = 1
        match_key_size = 8
    if add_uninteresting_header:
        dummy_ethernet = False

    cmd = [
        'python3', 'deps/p4gen16/generate.py', '-t', spec['program']['architecture'], '-o', outdir,
        '--default-egress-spec', str(spec['node_config']['dut']['port']['tx']),
        '--header-fields', str(number_header_fields),
        '--header-field-size', str(header_field_size),
        '--number-match-keys', str(number_match_keys),
        '--match-key-size', str(match_key_size),
        '--match-type', str(match_type),
        '--repeat-apply-tables', str(repeat_apply_tables),
        '--number-tables', str(number_tables),
        '--repeat-apply-tables', str(number_table_apply),
        '--number-table-entries', str(number_table_entries),
        '--number-action-data', str(action_data),
        '--deparser-add-headers', str(deparser_add_headers),
        '--deparser-remove-headers', str(deparser_remove_headers),
        '--deparser-add-headers-size', str(deparser_add_headers_size),
        '--header-field-modifies', str(header_field_writes),
        '--meta-field-modifies', str(meta_field_writes),
    ]
    if dummy_ethernet:
        cmd.append('--skip-ethernet')
        cmd.append('--skip-ip')
    if add_uninteresting_header:
        cmd.append('--add-uninteresting-header')
    if spec['program']['target']:
        cmd += ['--sub-target', spec['program']['target']]
    if skip_filling_tables:
        cmd += ['--skip-filling-tables']
    if no_emit:
        cmd += ['--no-emit']
    if action:
        cmd += ['--action', action]
    if default_action:
        cmd += ['--default-action', default_action]
    if match_last:
        cmd += ['--match-last']
    #log.debug(' '.join(cmd))
    subprocess.run(cmd, check=True)
    files = [
        {
            'to': os.path.join(dut_config_path, 'program.p4'),
            'copy': '/root/t4p4s/t4p4s/examples/synthetic{}.p4'.format('_' + suffix if suffix else ''),
            'device': DUT
        }, {
            'to': os.path.join(dut_config_path, 'controller'),
            'copy': '/root/t4p4s/t4p4s/src/hardware_dep/shared/ctrl_plane/dpdk_l2fwd_controller{}.c'.format('_' + suffix if suffix else ''),
            'device': DUT
        },
    ]
    if skip_filling_tables:
        files.append({
            'to': os.path.join(dut_config_path, 'controlplane.c.py'),
            'copy': '/root/t4p4s/t4p4s/src/hardware_indep/controlplane{}.c.py'.format('_' + suffix if suffix else ''),
            'device': DUT
        })
    return files


def copy_templates_to_experiment(files, subdir, outdir):
    for file in files:
        src = file['template']
        dst = file['to']
        log.debug('copying %s -> %s', src, dst)
        src = os.path.join(subdir, src)
        dst = os.path.join(outdir, dst)
        template = None
        if file.get('environment', 'default') == 'C':
            template = JINJA_C.get_template(src)
        else:
            # the default
            template = JINJA.get_template(src)
        with open(dst, 'w') as outf:
            variables = file.get('variables', {})
            outf.write(template.render(**variables))


def generate_loadgen(spec):
    log.info('Generating loadgen MoonGen files')

    # pos setup and variables
    testbed_manual = spec['meta']['testbed'] == 'manual'
    fixed_packet_size = spec['traffic']['packet_size'] if 'packet_size' not in spec['metrics']['scale'] else False
    files = [
        {
            'template': 'testbed/measurement.sh',
            'to': os.path.join(DIRS['lg'], 'measurement.sh'),
            'variables': {
                'testbed_manual': testbed_manual,
                'scale_table_entries': 'table_entries' in spec['metrics']['scale'],
                'scale_packet_size': 'packet_size' in spec['metrics']['scale'],
                'scale_load': 'load_rate' in spec['metrics']['scale'],
                'measure_latency': 'latency' in spec['metrics']['names'],
            }
        }, {
            'template': 'testbed/setup.sh',
            'to': os.path.join(DIRS['lg'], 'setup.sh')
        }, {
            'template': 'testbed/variables.yml',
            'to': os.path.join(DIRS['lg'], 'variables.yml'),
            'variables': {
                'port': {
                    'tx': spec['node_config']['loadgen']['port']['tx'],
                    'rx': spec['node_config']['loadgen']['port']['rx']
                },
                'packet_size': fixed_packet_size,
            }
        }, {
            'template': 'lua/max-load.lua',
            'to': os.path.join(DIRS['lg_script'], 'max-load.lua'),
            'copy': '/root/',
            'device': LG,
            'variables': {
                'payload_u32_offset': spec['traffic']['payload_u32_offset'],
            }
        }, {
            'template': 'lua/latency.lua',
            'to': os.path.join(DIRS['lg_script'], 'latency.lua'),
            'copy': '/root/',
            'device': LG,
            'variables': {
                'payload_u32_offset': spec['traffic']['payload_u32_offset'],
            }
        }, {
            'template': 'util/get_max_rate.py',
            'to': os.path.join(DIRS['lg_util'], 'get_max_rate.py'),
            'copy': '/root/',
            'device': LG,
            'variables': {
                'repetitions': spec['meta']['max_load_repetitions']
            }
        }, {
            'template': 'util/multiply_floats.py',
            'to': os.path.join(DIRS['lg_util'], 'multiply_floats.py'),
            'copy': '/root/',
            'device': LG
        },
    ]
    copy_templates_to_experiment(files, 'moongen', spec['meta']['outdir'])
    return files


def generate_t4p4s_setup(spec):
    log.info('Generating DuT t4p4s files')

    tx = spec['node_config']['dut']['port']['tx']
    rx = spec['node_config']['dut']['port']['rx']
    coremask = []
    portmask = '{0:X}'.format((1 << tx) | (1 << rx))
    cpq_map = []
    cores = spec['node_config']['dut']['cores']
    for i, _ in enumerate(cores):
        cmask = 0
        cpq = []
        for idx, coreid in enumerate(cores[0:i+1]):
            cmask |= 1 << coreid
            for port in [tx, rx]:
                cpq.append('({},{},{})'.format(port, idx, coreid))
        coremask.append('{0:X}'.format(cmask))
        cpq_map.append(','.join(cpq))

    default_commits = {
        't4p4s_commit': '0a6c455846f201432a53dc9347909ae933ec0b32',
        't4p4s_boots': '668019b8440fbbe4760194c7247492012455ae83',
        'hlir16': 'c9408db9b970493259e0b5cc27efc39063a73cd3',
        'p4c': 'ecba24ad591e719268860f66202530830d2a914e',
        'p4runtime': '',
        'protobuf': 'v3.9.2'
    }

    # pos setup and variables
    testbed_manual = spec['meta']['testbed'] == 'manual'
    multiple_programs = spec['program']['scale']['with'] if spec['program']['scale'] else False
    update_controlplane = any([key in spec['metrics']['scale'] for key in ['tables', 'table_entries', 'action_data']])
    increase_max_wait = any([key in spec['metrics']['scale'] for key in ['tables', 'meta_field_writes']])
    increase_wait = any([key in spec['metrics']['scale'] for key in ['tables', 'table_entries']])
    files = [
        {
            'template': 'testbed/measurement.sh',
            'to': os.path.join(DIRS['dut'], 'measurement.sh'),
            'variables': {
                'testbed_manual': testbed_manual,
                'multiple_programs': multiple_programs,
                'scale_frequency': 'cpu_frequency' in spec['metrics']['scale'],
                'update_controlplane': update_controlplane,
                'increase_max_wait': increase_max_wait,
                'increase_wait': increase_wait,
            }
        }, {
            'template': 'testbed/setup.sh',
            'to': os.path.join(DIRS['dut'], 'setup.sh'),
            'variables': {
                'testbed_manual': testbed_manual,
            }
        }, {
            'template': 'testbed/variables.yml',
            'to': os.path.join(DIRS['dut'], 'variables.yml'),
            'variables': {
                'port': {
                    'tx': tx,
                    'rx': rx
                },
                'cpu_frequency': max(spec['node_config']['dut']['cpu_frequencies']),
                'events': ','.join(spec['metrics']['perf'].keys()),
                'commits': default_commits,
            }
        }, {
            'template': 't4p4s/examples.cfg',
            'to': os.path.join(DIRS['dut_config'], 'examples.cfg'),
            'copy': '/root/t4p4s/t4p4s/',
            'device': DUT
        }, {
            'template': 't4p4s/opts_dpdk.cfg',
            'variables': {
                'coremasks': coremask,
                'portmask': portmask,
                'cpq_maps': cpq_map,
            },
            'to': os.path.join(DIRS['dut_config'], 'opts_dpdk.cfg'),
            'copy': '/root/t4p4s/t4p4s/',
            'device': DUT
        }, {
            'template': 't4p4s/rte.sdkinstall.mk',
            'to': os.path.join(DIRS['dut_config'], 'rte.sdkinstall.mk'),
            'for_setup': True,
            'copy': '/root/',
            'device': DUT
        }
    ]

    for i, _ in enumerate(cores):
        i += 1
        files.append({
            'template': 'testbed/run_perf_stat.sh',
            'variables': {
                'cores': ','.join(str(core) for core in cores[0:i])
            },
            'to': os.path.join(DIRS['dut'], 'run_perf_stat_{}.sh'.format(i)),
            'copy': '/root/run_perf_stat_{}.sh'.format(i),
            'device': DUT
        })

    # add fast way to insert table entries
    # increase table entries limit
    if spec['program']['args']['skip_filling_tables']:
        tables = 't4p4s/dpdk_tables.h'
        files += [{
                'template': tables,
                'to': os.path.join(DIRS['dut_config'], 'dpdk_tables.h'),
                'copy': '/root/t4p4s/t4p4s/src/hardware_dep/dpdk/includes/dpdk_tables.h',
                'device': DUT,
                'variables': {
                        'table_entries': 20000000 if 'table_entries' in spec['metrics']['scale'] else 1000
                    }
            }, {
                'template': 't4p4s/dpdk_lib_change_tables.c',
                'to': os.path.join(DIRS['dut_config'], 'dpdk_lib_change_tables.c'),
                'copy': '/root/t4p4s/t4p4s/src/hardware_dep/dpdk/data_plane/dpdk_lib_change_tables.c',
                'device': DUT
            }
        ]

    # this fixes a bug in the t4p4s code that no deparser modifications are performed
    if any([key in spec['metrics']['scale'] for key in ['added_headers', 'removed_headers', 'added_headers_size']]):
        files.append({
            'template': 't4p4s/dataplane.c.py',
            'environment': 'C',
            'variables': {
                'emit_reordering': True,
            },
            'to': os.path.join(DIRS['dut_config'], 'dataplane.c.py'),
            'copy': '/root/t4p4s/t4p4s/src/hardware_indep/dataplane.c.py',
            'device': DUT
        })

    bootparameters = [
        {
            'device': '${DUT}',
            'parameters': 'isolcpus=0-6 intel_pstate=disable default_hugepagesz=1G hugepagesz=1G hugepages=16',
        }
    ]

    copy_templates_to_experiment(files, 'p4_t4p4s', spec['meta']['outdir'])
    return files, bootparameters


def generate_pos_experiment(spec, previous_files, bootparameters=None):
    log.info('Generating pos experiment files')

    if not bootparameters:
        bootparameters = []

    # pos experiment script
    files_to_copy = [
        {'from': obj['to'], 'dest': obj['copy'], 'device': '${LG}' if obj['device'] == LG else '${DUT}'}
        for obj in previous_files if 'copy' in obj and not obj.get('for_setup', False)
    ]
    files_to_copy_setup = [
        {'from': obj['to'], 'dest': obj['copy'], 'device': '${LG}' if obj['device'] == LG else '${DUT}'}
        for obj in previous_files if 'copy' in obj and obj.get('for_setup', False)
    ]

    # pos setup and variables
    files = [
        {
            'template': 'experiment.sh',
            'variables': {
                'copy': files_to_copy,
                'copy_setup': files_to_copy_setup,
                'bootparameters': bootparameters,
                'experiment_name': '/'.join([spec['meta']['target'], spec['meta']['component'], spec['meta']['feature']])
            },
            'to': os.path.join(DIRS['experiment'], 'experiment.sh')
        }, {
            'template': 'command.sh',
            'variables': {
                'loadgen': spec['node_config']['loadgen']['name'],
                'dut': spec['node_config']['dut']['name']
            },
            'to': os.path.join(DIRS['experiment'], 'command.sh')
        }, {
            'template': 'global-variables.yml',
            'to': os.path.join(DIRS['experiment'], 'global-variables.yml'),
            'variables': {
                'scale_load': 'load_rate' in spec['metrics']['scale'],
                'repetitions': spec['meta']['max_load_repetitions']
            }
        },
    ]
    copy_templates_to_experiment(files, 'pos', spec['meta']['outdir'])
    return files


def create_directories(outdir):
    # directories
    log.info('Creating output directory')
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    log.info('Creating sub directories')
    for subdir in DIRS.values():
        os.makedirs(os.path.join(outdir, subdir), exist_ok=True)


def generate(spec):
    ## dirs
    create_directories(spec['meta']['outdir'])

    dump_specification(spec)

    files = []

    ## loadgen
    files += generate_loadgen(spec)

    ## DUT
    # p4 program
    scale = spec['program']['scale']
    if scale:
        for val in spec['metrics']['scale'][scale['with']]:
            spec['program']['args'][scale['arg']] = val
            generate_p4_planes(spec, suffix=str(val), **spec['program']['args'])
    else:
        generate_p4_planes(spec, **spec['program']['args'])

    # testbed setup for concrete target
    bootparameters = None
    if spec['meta']['target'] == 'p4_t4p4s':
        _files, bootparameters = generate_t4p4s_setup(spec)
        files += _files
    else:
        log.error('Testbed not yet supported')
        sys.exit(3)

    ## testbed setup
    # needs to take care of deploying all files and starting the measurements
    if spec['meta']['testbed'] == 'pos':
        files += generate_pos_experiment(spec, files, bootparameters=bootparameters)

    # variables that shall be looped over for this measurement series
    generate_loop_variables(spec)

    # generate evaluation
    generate_evaluation(spec)
