# Temporal Conversion Example
This repository demonstrates two versions of a traditional ticketing support system. The first
(in the "before-temporal" folder) is a synchronous version, 

## Project Files
  - `README.md` - This file. The one you're reading.
  - `original_system.py` - The purely synchronous, original Python version
  - `activities.py` - Temporal Activities
  - `client.py` - Script that puts tickets through the workflow
  - `models.py` - @dataclasses
  - `base_workflow.py` - Base workflow, with activity helpers
  - `workflow.py` - The main Temporal workflow
  - `worker.py` - The Temporal worker
  - `client.py` - For running tickets through the Temporal workflow from the cli
  - `requirements.txt` - Python dependencies. Namely temporal.
  - `start_worker.sh` - script that starts the Temporal worker within a virtual env

## Prerequisites
- I have only tested this on a Mac ARM laptop--I would think it works on Windows, except that the python commands are bound to be different
- Python 3.8+
- Temporal server running (scripts assume localhost:7233 -- edit worker.py and client.py to change)
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
python original_system.py
```

### Run a comparison between the original Python and  Temporal workflows
```bash
python comparison_demo.py
```

### Run the Temporal workflow
```bash
python client.py
```

### Bugs
- The workflow_id should be the ticket_id, rather than "ticket_id-uuid4", but it makes for nightmarish demos. This can be fixed once there's a database with a proper sequence
- ~~Critical - The "knowledge base failed" workflow (LowPriority) path is failing~~
- ~~Critical - The "no agents available" workflow (HighPriority) path is failing~~
- Urgent - When "agent reassignment" fails 3 times workflow (LowPriority), the child workflow fails, and doesn't follow the ApplicationError flow. Need advice on best practices. Happens 1 in ~30 times

### Improvements made since Nov 12:
- ✅ Workflow refinements, adding some ApplicationErrors to handle flow rather than if/then
- ✅ Need to break up the main workflow into low/med/high child workflows
- ✅ Break up monolithic workflow into parent/child
- ✅ Need to reduce the amount of code in the workflow--much of it is repetitive and boilerplate
- ✅ Group workers by where they exist in the org (support, internal, eng), not the nature of the worklows
- ✅ Need to refactor activity calls to encapsulate the repetitive utilities (activities, logging, queues)
- ✅ Logging improvements -- precision, level, terseness

## Improvements I'd like to make
- Heartbeats from long-running tasks
- Compensation activities for failed steps (if an agent takes too long to respond and we need to reassign, etc)
- Demonstration of race condition handling during API/db calls
- Pause/resume workflow - splitting parent/child workflows broke this--need to bring it back
- Real-time status queries
