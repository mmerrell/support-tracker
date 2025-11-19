# Temporal Conversion Example
This repository demonstrates two versions of a traditional ticketing support system. The first
(`original_system.py`) is a synchronous version, developed in Python (by Claude Sonnet 4). I then converted 
the workflow to Temporal in three phases. the `main` branch maps to `v3`. I kept the earlier versions to demonstrate
the evolution of the workflow, which could be instructive to other people learning how to implement Temporal workflows.

- `v1` - The initial implementation: ultra simple, giving basic Temporal functionality (workflows, activities, workers)
- `v2` - Some revisions, including breaking up central workflow into parent/child for more modular implementation 
- `v3` - Adding compensation steps, queries, and making small improvements (eliminating magic strings, making logging more precise)

## Project Files
  - `activities.py` - Temporal Activities
  - `base_workflow.py` - Base workflow, with activity helpers
  - `enums.py` - a number of enumerated types, to give real values to various states other than strings
  - `models.py` - @dataclasses
  - `original_system.py` - The purely synchronous, original Python version
  - `README.md` - This file. The one you're reading.
  - `requirements.txt` - Python dependencies. Namely temporal.
  - `run_demo.sh` - File for running the comparison demo
  - `run_temporal.py` - For running tickets through the Temporal workflow from the cli
  - `setup.sh` - script that starts venv, installs requirements, gets system ready
  - `start_worker.sh` - script that starts the Temporal worker within a virtual env
  - `worker.py` - The Temporal worker
  - `workflow.py` - The main Temporal workflow
  
## Prerequisites
- I have only tested this on a Mac ARM laptop--I would think it works on Windows, except that the python commands are bound to be different
- Python 3.8+
- Temporal server running (scripts assume localhost:7233 -- edit worker.py and run_temporal.py to change)
- `pip install temporalio`

## Initialize the environment
- git clone git@github.com:mmerrell/support-tracker.git
- `./setup.sh`
- This will initialize a venv, from which it is advised to run the Temporal worker as well as the demo scripts

## Running the Examples
In one terminal, start the Temporal worker:
`./start_worker.py` -- this will launch the Temporal worker within the venv created by setup.sh 

### Run the original workflow by itself
```bash
python original_system.py -- this will launch the original Python version's `main()` method with ~3 tickets, serially
```

### Run the Temporal workflow
```bash
python run_temporal.py -- this will run 30 tickets through the Temporal system in parallel
```

### Bugs
- The workflow_id should be the ticket_id, rather than "ticket_id-uuid4", but it makes for nightmarish demos. This can be fixed once there's a database with a proper sequence
- ~~Critical - The "knowledge base failed" workflow (LowPriority) path is failing~~
- ~~Critical - The "no agents available" workflow (HighPriority) path is failing~~
- ~~Urgent - When "agent reassignment" fails 3 times workflow (LowPriority), the child workflow fails, and doesn't follow the ApplicationError flow~~

### Improvements made since v1 (Nov 12):
- ✅ Workflow refinements, adding some ApplicationErrors to handle flow rather than if/then
- ✅ Need to break up the main workflow into low/med/high child workflows
- ✅ Break up monolithic workflow into parent/child
- ✅ Need to reduce the amount of code in the workflow--much of it is repetitive and boilerplate
- ✅ Group workers by where they exist in the org (support, internal, eng), not the nature of the worklows
- ✅ Need to refactor activity calls to encapsulate the repetitive utilities (activities, logging, queues)
- ✅ Logging improvements -- precision, level, terseness
- ✅ 2 compensation steps - one for releasing an agent after they fail to investigate, and one to notify the customer that they need to escalate
- ✅ Status now belongs to workflow, not Ticket. I can't believe I didn't see that before. Real-time queries available now

## Improvements I'd like to make
- Heartbeats from long-running tasks
- Demonstration of race condition handling during API/db calls
- Pause/resume workflow - splitting parent/child workflows broke this--need to bring it back from v1
- Can I suppress stacktraces from logs?
