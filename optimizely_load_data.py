import os
import datetime
from pytz import timezone
import pandas as pd
from azure.devops.credentials import BasicAuthentication
from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.models import Wiql

__VERSION__ = "1.0.0"
auth_token = os.environ['AZURE_DEVOPS_PAT']
url ="https://dev.azure.com/skanskanordic/"
increment = "Skanska Sverige IT\\2023\Höst 2023-3"
areas = ["Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services",
         "Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\Brand Hub Web",
         "Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\Corporate Web",
         "Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\Enterprise Search Global",
         "Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\Microsites Web",
         "Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\OneSkanska",
         "Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\Web Development Environment"]
#areas = ["Skanska Sverige IT\\Development and Operations\\Global Services\\Global Digital Communication Services\\Corporate Web" ]
increment = "Skanska Sverige IT\\2023\Höst 2023-3"
# Three exact times, 1 after the sprint planning meeting, before sprint demo , after next sprints planning
sprint = ("Sprint 1", datetime.datetime(2023,9,  6,10,0, tzinfo=timezone('UTC')), datetime.datetime(2023, 9,15,0,0, tzinfo=timezone('UTC')), datetime.datetime(2023, 9,18,12,0, tzinfo=timezone('UTC')) )
sprint = ("Sprint 2", datetime.datetime(2023,9, 18,12,0, tzinfo=timezone('UTC')), datetime.datetime(2023, 9,29,0,0, tzinfo=timezone('UTC')), datetime.datetime(2023,10, 2, 9,0, tzinfo=timezone('UTC')) )
sprint = ("Sprint 3", datetime.datetime(2023,10, 2, 9,0, tzinfo=timezone('UTC')), datetime.datetime(2023,10,13,0,0, tzinfo=timezone('UTC')), datetime.datetime(2023,10,16, 8,0, tzinfo=timezone('UTC')) )
sprint = ("Sprint 4", datetime.datetime(2023,10, 16,8,0, tzinfo=timezone('UTC')), datetime.datetime(2023,10,27,0,0, tzinfo=timezone('UTC')), datetime.datetime(2023,10,30, 8,0, tzinfo=timezone('UTC')) )
sprint = ("Sprint 5", datetime.datetime(2023,10, 30,8,0, tzinfo=timezone('UTC')), datetime.datetime(2023,11,10,0,0, tzinfo=timezone('UTC')), datetime.datetime(2023,11,13, 8,0, tzinfo=timezone('UTC')) )

from types import SimpleNamespace
context = SimpleNamespace()
context.runner_cache = SimpleNamespace()
context.connection = Connection(base_url=url,creds=BasicAuthentication('PAT', auth_token), user_agent='azure-devops-python-samples/' + __VERSION__)


desired_ids = list()
wit_client = context.connection.clients.get_work_item_tracking_client()
for area in areas:
    wiql = Wiql(query="SELECT [System.Id] from WorkItems WHERE [System.AreaPath] = '"+area+"' AND [System.IterationPath] under '"+increment+"' AND [System.WorkItemType] = 'Task'")
    wiql_results = wit_client.query_by_wiql(wiql, top=1000).work_items
    if wiql_results:       
        for item in wiql_results: desired_ids.append(int(item.id))

workitems_after_planning = list()
workitems_before_demo= list()
workitems_after_demo= list()
start = 0 
stop = 0
max = len(desired_ids)-1
while stop<max:
    if (start+100)<=max: stop = start+99  
    else:                stop = stop+(len(desired_ids) - start)
    workitems_after_planning += wit_client.get_work_items(ids=desired_ids[start:stop], as_of=sprint[1], error_policy="omit" )
    workitems_before_demo    += wit_client.get_work_items(ids=desired_ids[start:stop], as_of=sprint[2], error_policy="omit" ) #2:00
    workitems_after_demo     += wit_client.get_work_items(ids=desired_ids[start:stop], as_of=sprint[3], error_policy="omit" ) #
    start+=100

def getTasks(workitems):
    result = list()
    for item in workitems:
        if (item is None): continue
        result.append(
            {
                "id": item.id,
                "area": item.fields["System.AreaPath"].split('\\')[-1],
                "iteration": item.fields["System.IterationPath"].split('\\')[-1],
                "title": item.fields["System.Title"],
                "state.start": item.fields["System.State"],
                "state.end": item.fields["System.State"],
                "resource": item.fields["System.AssignedTo"]["displayName"] if "System.AssignedTo" in item.fields else "", 
                "estimate": item.fields["Microsoft.VSTS.Scheduling.OriginalEstimate"] if "Microsoft.VSTS.Scheduling.OriginalEstimate" in item.fields else "", 
                "completed": item.fields["Microsoft.VSTS.Scheduling.CompletedWork"] if "Microsoft.VSTS.Scheduling.CompletedWork" in item.fields else "",
                "remaining" : item.fields["Microsoft.VSTS.Scheduling.RemainingWork"] if "Microsoft.VSTS.Scheduling.RemainingWork" in item.fields else "",
                "activated" : item.fields["Microsoft.VSTS.Common.ActivatedDate"] if "Microsoft.VSTS.Common.ActivatedDate" in item.fields else "",
                "resolved": item.fields["Microsoft.VSTS.Common.ResolvedDate"] if "Microsoft.VSTS.Common.ResolvedDate" in item.fields else ""
            })  
    return result

tasks_after_planning = pd.DataFrame(getTasks(workitems_after_planning))
tasks_before_demo = pd.DataFrame(getTasks(workitems_before_demo))
tasks_after_demo = pd.DataFrame(getTasks(workitems_after_demo))

df = pd.merge(tasks_after_planning,tasks_after_demo , on="id", how="right") 
df = pd.merge(df,tasks_before_demo , on="id", how="right") 
df['estimate_z'] = df['estimate_x'].where(df['estimate_x'].notnull(), df['estimate'])
df = df[['id', 'area_y', 'iteration_y', 'title_y','state.start_x', 'state.end_y', 'resource_y','estimate_z','completed_y', 'remaining_y', 'activated_y', 'resolved_y'  ]]
df = df.rename(columns={'area_y': 'area', 'iteration_y': 'iteration', 'title_y': 'title', 'state.start_x': 'state.start', 'state.end_y': 'state.end', 'resource_y': 'resource', 'estimate_z': 'estimate', 'completed_y': 'completed', 'remaining_y': 'remaining', 'activated_y': 'activated', 'resolved_y': 'resolved'})
df = df.replace("NaN", 0)

df['estimate'].replace('',0)
df['completed'].replace('',0)
df['remaining'].replace('',0)

df['estimate'] = pd.to_numeric(df['estimate'])
df['completed'] = pd.to_numeric(df['completed'])
df['remaining'] = pd.to_numeric(df['remaining'])

df.to_csv("tasks_" + sprint[0] + ".csv", sep=";", decimal=',')