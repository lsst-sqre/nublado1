#!/usr/bin/env python
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
    dep = JupyterLabDeployment(params={})
    dep.params['hostname'] = "kremvax.ru"
    dep._validate_deployment_params()
    assert dep._empty_param('missing')
    assert not dep._empty_param('hostname')


def test_default_cluster_name():
    dep = JupyterLabDeployment(params={})
    dep.params['hostname'] = "kremvax.ru"
    dep._validate_deployment_params()
    assert dep.params['kubernetes_cluster_name'] == "kremvax-ru"


def test_default_cluster_namespace():
    dep = JupyterLabDeployment(params={})
    dep.params['hostname'] = "kremvax.ru"
    dep._validate_deployment_params()
    assert dep.params['kubernetes_cluster_namespace'] == 'default'
