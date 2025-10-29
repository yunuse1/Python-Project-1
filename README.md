# Check Universities Price Automation

This repository contains python-gauge tests for the Odepro project

## Prerequest

* highest Python3.8.x (brew install python3)
* pip (pip3)

## Installing Gauge

### Install Using HomeBrew (Preferred)

Install [brew](https://brew.sh), and run the following command

```bash
brew install gauge
```

### Install Using CURLgauge

Install Gauge to `/usr/local/bin` by running

```bash
curl -Ssl https://downloads.gauge.org/stable | sh
```

## Create and Install Requirements

Create a virtual environment:

```bash
python -m venv venv
```

Enter the virtual environment:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Deactivate venv:

```bash
deactivate
```

## Run specifications by using directory(s) as an argument

Specifications can be run from a single directory, sub-directories, or multiple directories. You can specify the directory(s) or path to sub-directory(s) with the gauge run command.

To run all the specifications in the specs directory, use the following command:

```bash
gauge run specs
```

To run specifications at the sub-directory level, use the following command:

```bash
gauge run <path_dir>
```

## Run specifications by using spec file path as argument

You can choose and run only certain specifications by providing the appropriate location of these specifications with the gauge run command.

```bash
gauge run <path_to_spec>
```

## Run a Gauge specification with an environment

You can use the -env flag to load an environment when Gauge runs a specification. If -env is not specified, then the `default` environment is loaded during run time.

```bash
gauge run --env <test_environment> specs
```

For more execution options see [here](https://docs.gauge.org/execution.html)

## PEP-80 Controlling

To control where pep-80 pipeline fails please check
```bash
python3 -m pycodestyle step_impl
```

## Protofiles for grpc

```bash
git submodule update --init
```

## Generated grpc protofiles

```bash
buf generate
```

## Run a Gauge specification with HTTP or GRPC

Change CLIENT from localhost.properties to HTTP or GRPC

