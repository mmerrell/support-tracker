# Temporal Conversion Example
This repository demonstrates two versions of a traditional ticketing support system. The first
(in the "before-temporal" folder) is a synchronous version, 

## Project Files
  - `README.md` - This file. The one you're reading.
  - `original_system.py` - The purely synchronous, original Python version
  - `activities.py` - Temporal Activities
  - `client.py` - Script that puts tickets through the workflow
  - `models.py` - @dataclasses
  - `workflow.py` - The main Temporal workflow
  - `worker.py` - The Temporal worker
  - `client.py` - For running tickets through the Temporal workflow from the cli
  - `requirements.txt` - Python dependencies. Namely temporal.
  - `start_worker.sh` - script that starts the Temporal worker within a virtual env
  - `run_demo.sh` - script that runs the comparison demo within a virtual env

## Prerequisites
- I have only tested this on a Mac ARM laptop--I would think it works on Windows, except that the python commands are bound to be different
- Python 3.8+
- Temporal server running (scripts assume localhost:7233 -- edit worker.py, comparison_demo.py and client.py to change)
- `pip install temporalio`

## Initialize the environment
- git clone git@github.com:mmerrell/support-tracker.git
- `./setup.sh`
- This will initialize a venv, from which it is advised to run the Temporal worker as well as the demo scripts

## Running the Examples
In one terminal, start the Temporal worker:
`./start_worker.py` -- this will launch the Temporal worker within the venv created by setup.sh 

In a separate terminal, start the comparison demo:
`./run_demo.sh` -- this will launch the demo script within the same venv

### Run the original workflow by itself
```bash
python original_system.py
```

### Run the Temporal workflow by itself
```bash
python client.py
```

### Comparison Demo
```bash
python comparison_demo.py
```
Compare the before and after implementations to see how Temporal addresses:
- Durability during failures
- Automatic retries
- State management
- Error handling
- Scalability (see note, below) 

### Interactive Demo
```bash
python interactive_demo.py
```
Demonstrates the ability to pause and resume a Temporal workflow mid-stream. Pause it for minutes, 
hours, or days, and it will resume right where it left off, with no load on any CPUs, no wait logic,
no regular polling. This demo will also let you get the state of the workflow wherever it is at the
moment.

### Bugs
- ~~The "pause" mechanism wait for the status to change to the next step for actually pausing the workflow. This gave a misleading indication of the actual state of the workflow~~
- The workflow_id should be the ticket_id, rather than "ticket_id-uuid4". This would help Temporal to force the primary key constraint on ticket id. But it's possible this is an anti-pattern--I can understand why that should only be enforced at the db layer (separation of concerns)

### Improvements made since Nov 12:
- ✅ Looking at it again, the if/else block for the knowledge base search needs more Temporal-idiomatic structure
- ✅ Need to break up the main workflow into low/med/high child workflows
- ✅ Break up monolithic workflow into parent/child
- ✅ Need to reduce the amount of code in the workflow--much of it is repetitive and boilerplate
- ✅ Group workers by where they exist in the org (support, internal, eng), not the nature of the worklows

## Improvement I'd like to make
- More nuanced retry mechanisms
- Heartbeats from long-running tasks
- Compensation activities for failed steps (if an agent takes too long to respond and we need to reassign, etc)
- Demonstration of race condition handling during API/db calls
- Need to fix the Medium priority flow to use exceptions like the low flow
- Need to refactor activity calls to encapsulate the repetitive utilities (pausing, steps, logging, queues)