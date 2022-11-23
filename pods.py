#!/usr/bin/python3.11
import sys
import tomllib as toml
import os
import re
from dotenv import dotenv_values
from podman import PodmanClient

def load_config(path):
  with open(path, 'rt') as file:
    text = file.read()
    env = dotenv_values()
    for string in set(re.findall(r'\${.*?}', text)):
      text = text.replace(string, env[string[2:-1]])
    return toml.loads(text)

def parse_port_mapping(mapping):
  match mapping.count('/'):
    case 0: protocol = 'tcp'
    case 1: mapping, protocol = mapping.split('/')
    case _: raise ValueError('invalid port mapping syntax')
  match mapping.count(':'):
    case 1: host_ip, [host_port, container_port] = None, mapping.split(':')
    case 2: host_ip, host_port, container_port = mapping.split(':')
    case _: raise ValueError('invalid port mapping syntax')

  return {
    'host_ip': host_ip,
    'host_port': int(host_port),
    'container_port': int(container_port),
    'protocol': protocol,
  }

def parse_volume(volume):
  match volume.count(':'):
    case 1: [host_path, container_path], option = volume.split(':'), 'rw'
    case 2: host_path, container_path, option = volume.split(':')
    case _: raise ValueError('invalid volume syntax')

  if not (host_path.startswith('./') or host_path.startswith('/')):
    raise ValueError('invalid volume syntax')

  host_path = os.path.abspath(host_path)

  match option:
    case 'rw': read_only = False
    case 'ro': read_only = True
    case _: raise ValueError('invalid volume syntax')

  return {
    'type': 'bind',
    'source': host_path,
    'target': container_path,
    #'read_only': read_only, # below is used instead b/c of a bug; will be readonly if read_only is defined, regardless of value
    **({ 'read_only': True } if read_only else {})
  }

def up_all(client):
  name = config['name']
  for pod_name, path in config['pods'].items():
    pod = load_config(path)
    client.pods.create(
      name=f'{name}.{pod_name}',
      network_options={ 'slirp4netns': [ 'port_handler=slirp4netns', 'allow_host_loopback=true' ] },
      portmappings=[ parse_port_mapping(p) for p in pod.get('ports', []) ])
    for container_name, container in pod['containers'].items():
      client.containers.run(
        name=f'{name}.{pod_name}.{container_name}',
        image=container['image'],
        command=container.get('command'),
        user=container.get('user'),
        mounts=[ parse_volume(v) for v in container.get('volumes', []) ],
        environment=container.get('env', {}),
        pod=f'{name}.{pod_name}',
        detach=True)


def up(client, pod_name):
  name = config['name']
  if pod_name not in config['pods']:
    print(f'{pod_name} is not a pod')
    return
  pod = load_config(config['pods'][pod_name])
  client.pods.create(
    name=f'{name}.{pod_name}',
    network_options={ 'slirp4netns': [ 'port_handler=slirp4netns', 'allow_host_loopback=true' ] },
    portmappings=[ parse_port_mapping(p) for p in pod.get('ports', []) ])
  for container_name, container in pod['containers'].items():
    client.containers.run(
      name=f'{name}.{pod_name}.{container_name}',
      image=container['image'],
      command=container.get('command'),
      user=container.get('user'),
      mounts=[ parse_volume(v) for v in container.get('volumes', []) ],
      environment=container.get('env', {}),
      pod=f'{name}.{pod_name}',
      detach=True)

def down_all(client):
  name = config['name']
  for pod_name in config['pods']:
    try:
      pod = client.pods.get(f'{name}.{pod_name}')
      pod.stop()
      pod.remove()
    except:
      continue


def down(client, pod_name):
  name = config['name']
  if pod_name not in config['pods']:
    print(f'{pod_name} is not a pod')
    return
  try:
    pod = client.pods.get(f'{name}.{pod_name}')
    pod.stop()
    pod.remove()
  except:
    pass


config = load_config('pods.toml')

with PodmanClient() as client:
  if len(sys.argv) < 2:
    print('most supply parameters')
  elif len(sys.argv) == 2:
    match sys.argv[1]:
      case 'up': up_all(client)
      case 'down': down_all(client)
      case 'restart':
        down_all(client)
        up_all(client)
      case _: print(f'invalid option {sys.argv[1]}, valid options: up, down, restart')
  elif len(sys.argv) == 3:
    match sys.argv[1]:
      case 'up': up(client, sys.argv[2])
      case 'down': down(client, sys.argv[2])
      case 'restart':
        down(client, sys.argv[2])
        up(client, sys.argv[2])
      case _: print(f'invalid option {sys.argv[1]}, valid options: up, down, restart')
  else:
    print('TODO')

