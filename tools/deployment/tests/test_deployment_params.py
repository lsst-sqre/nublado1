#!/usr/bin/env python3
"""Test deployment parameter manipulation.
"""
import pytest
from jld_deploy import JupyterLabDeployment


def test_missing_params():
    """Test deployment without any parameters at all.
    """
    dep = JupyterLabDeployment()
    assert dep.params is None


def test_missing_hostname():
    """Test deployment parameters without a hostname.
    """
    dep = JupyterLabDeployment(params={})
    assert(dep)

    with pytest.raises(ValueError):
        dep._validate_deployment_params()


def test_empty_param_method():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru"})
    dep._validate_deployment_params()
    assert dep._empty_param('missing')
    assert not dep._empty_param('hostname')


def test_default_cluster_name():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru"})
    dep._validate_deployment_params()
    assert dep.params['kubernetes_cluster_name'] == "kremvax-ru"


def test_explicit_cluster_name():
    dep = JupyterLabDeployment(params={"hostname": "westwing.ru"})
    dep._validate_deployment_params()
    assert dep.params['kubernetes_cluster_name'] == "westwing-ru"


def test_default_cluster_namespace():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru"})
    dep._validate_deployment_params()
    assert dep.params['kubernetes_cluster_namespace'] == 'default'


def test_explicit_cluster_namespace():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "kubernetes_cluster_namespace":
                                       "raskolnikov"})
    dep._validate_deployment_params()
    assert dep.params['kubernetes_cluster_namespace'] == 'raskolnikov'


def test_filesystem_default_size():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru"})
    dep._validate_deployment_params()
    assert dep.params['volume_size_gigabytes'] == 20


def test_filesystem_illegal_size():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "volume_size_gigabytes": -2})
    with pytest.raises(ValueError):
        dep._validate_deployment_params()


def test_filesystem_calculate_sizes():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "github_organization_whitelist":
                                       "nkvd"})
    dep._validate_deployment_params()
    dep._normalize_params()
    assert dep.params['volume_size'] == '20Gi'
    assert dep.params['nfs_volume_size'] == '19Gi'
    dep.params['volume_size_gigabytes'] = 1
    dep._normalize_params()
    assert dep.params['volume_size'] == '1Gi'
    assert dep.params['nfs_volume_size'] == '950Mi'
    dep.params['volume_size_gigabytes'] = 1392
    dep._normalize_params()
    assert dep.params['volume_size'] == '1392Gi'
    assert dep.params['nfs_volume_size'] == '1322Gi'


def test_github_organization_whitelist():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru"})
    dep._validate_deployment_params()
    with pytest.raises(KeyError):
        dep._normalize_params()
    dep.params['github_organization_whitelist'] = []
    dep._validate_deployment_params()
    dep._normalize_params()
    assert dep.params['github_organization_whitelist'] == ''
    dep.params['github_organization_whitelist'] = ['nkvd']
    dep._validate_deployment_params()
    dep._normalize_params()
    assert dep.params['github_organization_whitelist'] == 'nkvd'
    dep.params['github_organization_whitelist'] = ['nkvd', 'kgb']
    dep._validate_deployment_params()
    dep._normalize_params()
    assert dep.params['github_organization_whitelist'] == 'nkvd,kgb'


def test_callback_url():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "github_organization_whitelist":
                                       "nkvd"})
    dep._validate_deployment_params()
    dep._normalize_params()
    assert dep.params['github_callback_url'] == (
        "https://kremvax.ru/hub/oauth_callback")


def test_enable_firefly():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "github_organization_whitelist":
                                       "nkvd"})
    dep._validate_deployment_params()
    dep._normalize_params()
    dep._check_optional()
    assert not dep.enable_firefly
    dep.params['firefly_admin_password'] = 'hunter2'
    dep._check_optional()
    assert dep.enable_firefly


def test_enable_logging():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "github_organization_whitelist":
                                       "nkvd"})
    dep._validate_deployment_params()
    dep._normalize_params()
    dep._check_optional()
    assert not dep.enable_logging
    for l in ['rabbitmq_pan_password',
              'rabbitmq_target_host',
              'rabbitmq_target_vhost',
              'log_shipper_name',
              'beats_key',
              'beats_ca',
              'beats_cert']:
        dep.params[l] = 'da, tovarisch'
    dep._check_optional()
    assert dep.enable_logging


def check_default_options():
    dep = JupyterLabDeployment(params={"hostname": "kremvax.ru",
                                       "github_organization_whitelist":
                                       "nkvd"})
    dep._validate_deployment_params()
    dep._normalize_params()
    dep._check_optional()
    assert dep.params['dhparam_bits'] == 2048
    assert dep.params['session_db_url'] == ('sqlite:////home/jupyter' +
                                            '/jupyterhub.sqlite')
