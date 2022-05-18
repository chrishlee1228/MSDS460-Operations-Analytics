'''  Coffee Shop Simulation with Balking 

Revised by Thomas W. Miller, May 13, 2022

Illustrate discrete event simulation of a simple queue
as needed for the study of business processes

SimPy reference manual:
Team SimPy. 2020, April 15. SimPy Documentation, Release 4.01. 
Retrieved from the World Wide Web, February 15, 2022 at
https://readthedocs.org/projects/simpy/downloads/pdf/stable/

'''
# let the simulation time unit be one second, but set parameters in minutes
# set global variables that do not change througout the course of the simulation

baristas = 1  # number of barista server resources... vary from 1 to 3

minimum_service_time = 1 # minutes (60 seconds)
mean_service_time = 2 # minutes (120 seconds)
maximum_service_time = 5 # minutes (300 seconds)

mean_inter_arrival_time = 1 # vary from 1 to 10 minutes (60 to 600 seconds)

balking_queue_length = 10  # longest queue length that customers will tolerate

# this binary toggle allows you to fix the random number seed
# so that every run of the program with specific parameter settings
# will yield the same results... setting to false will allow the
# program to obtain different results with each run
obtain_reproducible_results = True

# set length of simulation in simulation time units (assume seconds)
# run for similation_hours of simulation time
simulation_hours = 10
fixed_simulation_time =  simulation_hours*60*60   

parameter_string_list = [str(simulation_hours),'hours',
              str(baristas),str(minimum_service_time),
              str(mean_service_time),str(maximum_service_time),
              str(mean_inter_arrival_time),str(balking_queue_length)]
separator = '-'        
simulation_file_identifier = separator.join(parameter_string_list)

# initialize queue length
# queue_length = 0

import numpy as np # for random number distributions
import pandas as pd # for event_log data frame
pd.set_option('display.max_rows', 20)
pd.set_option('display.max_columns', 10)
import queue # add FIFO queue data structure
from functools import partial, wraps

import simpy # discrete event simulation environment

# user-defined function for random service time (modified exponential)
# returns real number of minutes
def random_service_time(minimum_service_time,mean_service_time,maximum_service_time) :
    try_service_time = np.random.exponential(scale = mean_service_time)
    if (try_service_time < minimum_service_time):
        return(minimum_service_time)
    if (try_service_time > maximum_service_time):
        return(maximum_service_time)
    if (try_service_time >= minimum_service_time) and (try_service_time <= maximum_service_time):
        return(try_service_time)
    
def arrival(env, caseid, caseid_queue, event_log):
    # generates new customers... arrivals
    caseid = 0
    while True:  # infinite loop for generating arrivals
        # get the service process started
        # must have waiting customers to begin service
    
        # schedule the time of next customer arrival       
        # by waiting until the next arrival time from now
        # when the process yields an event, the process gets suspended
        inter_arrival_time = round(60*np.random.exponential(scale = mean_inter_arrival_time))
        print("NEXT ARRIVAL TIME: ", env.now + inter_arrival_time)

        yield env.timeout(inter_arrival_time)  # generator function waits
        # env.timeout does not advance the clock. when an event/process calls env.timeout, 
        # that process waits until the clock gets to that time, it does not block 
        # other agents from doing stuff. Other processes can still do stuff 
        # while the first process is waiting for env.timeout to finish.
        caseid += 1
        time = env.now
        activity = 'arrival'
        env.process(event_log_append(env, caseid, time, activity, event_log)) 
        yield env.timeout(0) 
        if caseid_queue.qsize() < balking_queue_length:
            caseid_queue.put(caseid)          
            print("Customer joins queue caseid =",caseid,'time = ',env.now,'queue_length =',caseid_queue.qsize())
            time = env.now
            activity = 'join_queue'
            env.process(event_log_append(env, caseid, time, activity, event_log)) 
            env.process(service_process(env,  caseid_queue, event_log))       
        else:
            print("Customer balks caseid =",caseid,'time = ',env.now,'queue_length =',caseid_queue.qsize()) 
            env.process(event_log_append(env, caseid, env.now, 'balk', event_log)) 

def service_process(env, caseid_queue, event_log):
    # must have baristas to provide service... freeze until request can be met
    with available_baristas.request() as req:
        yield req  # wait until the request can be met.. there must be an available barista
        queue_length_on_entering_service = caseid_queue.qsize()
        caseid = caseid_queue.get()
        print("Begin_service caseid =",caseid,'time = ',env.now,'queue_length =',queue_length_on_entering_service)
        env.process(event_log_append(env, caseid, env.now, 'begin_service', event_log)) 
        # schedule end_service event based on service_time
        service_time = round(60*random_service_time(minimum_service_time,mean_service_time,maximum_service_time))   
        yield env.timeout(service_time)  # sets begin_service as generator function
        queue_length_on_leaving_service = caseid_queue.qsize()
        print("End_service caseid =",caseid,'time = ',env.now,'queue_length =',queue_length_on_leaving_service)
        env.process(event_log_append(env, caseid, env.now, 'end_service', event_log))

'''        
---------------------------------------------------------
set up event tracing of all simulation program events 
controlled by the simulation environment
that is, all timeout and process events that begin with "env."
documentation at:
  https://simpy.readthedocs.io/en/latest/topical_guides/monitoring.html#event-tracing
  https://docs.python.org/3/library/functools.html#functools.partial
'''
def trace(env, callback):
     """Replace the ``step()`` method of *env* with a tracing function
     that calls *callbacks* with an events time, priority, ID and its
     instance just before it is processed.
     note: "event" here refers to simulaiton program events

     """
     def get_wrapper(env_step, callback):
         """Generate the wrapper for env.step()."""
         @wraps(env_step)
         def tracing_step():
             """Call *callback* for the next event if one exist before
             calling ``env.step()``."""
             if len(env._queue):
                 t, prio, eid, event = env._queue[0]
                 callback(t, prio, eid, event)
             return env_step()
         return tracing_step

     env.step = get_wrapper(env.step, callback)

def trace_monitor(data, t, prio, eid, event):
     data.append((t, eid, type(event)))

def test_process(env):
     yield env.timeout(1)

'''
---------------------------------------------------------
set up an event log for recording events
as defined for the discrete event simulation
we use a list of tuples for the event log
documentation at:
  https://simpy.readthedocs.io/en/latest/topical_guides/monitoring.html#event-tracing
'''     
def event_log_append(env, caseid, time, activity, event_log):
    event_log.append((caseid, time, activity))
    yield env.timeout(0)
         
'''
---------------------------------------
set up the SimPy simulation environment
and run the simulation with monitoring
---------------------------------------
'''
if obtain_reproducible_results: 
    np.random.seed(9999)

# set up simulation trace monitoring for the simulation
data = []
# bind *data* as first argument to monitor()
this_trace_monitor = partial(trace_monitor, data)

env = simpy.Environment()
trace(env, this_trace_monitor)

env.process(test_process(env))

# implement FIFO queue to hold caseid values
caseid_queue = queue.Queue()

# set up limited server/baristas resource
available_baristas = simpy.Resource(env, capacity = baristas)
caseid = -1  # dummy caseid for beginning of simulation
# dummy caseid values will be omitted from the event_log
# prior to analyzing simulation results

# beginning record in event_log list of tuples of the form
# form of the event_log tuple item: (caseid, time, activity)
event_log = [(caseid,0,'null_start_simulation')]
# event_monitor = partial(event_monitor, event_log)
env.process(event_log_append(env, caseid, env.now, 'start_simulation', event_log))
 
# call customer arrival process/generator to begin the simulation
env.process(arrival(env, caseid, caseid_queue, event_log))  

env.run(until = fixed_simulation_time)  # start simulation with monitoring and fixed end-time

'''
-----------------------------------------------------------------
report simulation program results to data frame and files

the SimPy simiulation trace file provides a trace of events 
that is saved to a text file in the form
  (simulation time, index number of event, <class 'type of event'>)
this can be useful in debugging simulation program logic

the event_log list of tuples is saved to a text file of the form
  (caseid, time, 'activity')
the event_log list of tuples is also unpacked and saved as a
pandas data frame and saved to a comma-delimited text file 

-----------------------------------------------------------------
'''
simulation_trace_file_name = 'simulation-program-trace-' + simulation_file_identifier + '.txt'
with open(simulation_trace_file_name, 'wt') as ftrace:
    for d in data:
        print(str(d), file = ftrace)
print()        
print('simulation program trace written to file:',simulation_trace_file_name)

# convert list of tuples to list of lists
event_log_list = [list(element) for element in event_log]

# convert to pandas data frame
caseid_list = []
time_list = []
activity_list = []
for d in event_log_list:
    if d[0] > 0:
        caseid_list.append(d[0])
        time_list.append(d[1])
        activity_list.append(d[2])
event_log_df = pd.DataFrame({'caseid':caseid_list,
                             'time':time_list,
                             'activity':activity_list})    
print()
print('event log stored as Pandas data frame: event_log_df')

# save event log to comma-delimited text file
event_log_file_name = 'simulation-event-log-' + simulation_file_identifier + '.csv'
event_log_df.to_csv(event_log_file_name, index = False)  
print()
print('event log written to file:',event_log_file_name)

'''
-----------------------------------------------------------------
analyze simulation results 

here we report settings of simulation parameters and
compute summary statistics for the coffee shop

an additional output file provides a case-by-case listing
of all events in the event log

-----------------------------------------------------------------
'''
print()
print('Simulation parameter settings:')
print(baristas, 'baristas/servers')
print('  Service time settings (in minutes)')
print('    minimum:',minimum_service_time)
print('    mean:   ',mean_service_time)
print('    maximum:',maximum_service_time)
print('mean observed service times may deviate from the parameter setting')
print('due to censoring associated with the minimum and maxium')
print()
print('Customers set to arrive every', mean_inter_arrival_time, 'minute(s) on average')
print('Customers will not join the queue/waiting line if it has',balking_queue_length, 'customers in it (balking)')
print('The simulation is set to run for ', simulation_hours,' hours (',60*simulation_hours,' minutes)', sep ='')
print()
end_time = np.max(event_log_df["time"])
print('Results after ',end_time, ' seconds (', round(end_time/60, 2), ' minutes, ',round(end_time/(60*60),2),' hours):', sep = '')
caseid_list = pd.unique(event_log_df['caseid'])
print(len(caseid_list), 'unique customers arrived')
print(len(event_log_df['activity'][event_log_df['activity']=='join_queue']),'customers joined the queue for service')
print(len(event_log_df['activity'][event_log_df['activity']=='balk']),'customers balked (lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='begin_service']),'customers began service')
print(len(event_log_df['activity'][event_log_df['activity']=='end_service']),'customers ended service')
print(caseid_queue.qsize(),'customers were still in line at the end of the simulation')

# case-by-case logs are very useful for checking the logic of the simulation
case_by_case_event_file_name = 'simulation-program-case-by-case-events-' + simulation_file_identifier + '.txt'
with open(case_by_case_event_file_name, 'wt') as fcasedata:
    lastcase_arrival_time = 0  # initialize for use with first case
    # create lists for storing time interval data 
    inter_arrival_times = [] # computed across cases
    waiting_time = [] # computed within each case that has begun service
    service_time = [] # computed within each case that has ended service
    for thiscase in caseid_list:
        # select subset of rows for thiscase and use as a Pandas data frame
        thiscase_events = event_log_df[['caseid','time','activity']][event_log_df['caseid']==thiscase]
        print(file = fcasedata)
        print('events for caseid',thiscase, file = fcasedata)
        print(thiscase_events, file = fcasedata) 
        # compute inter-arrival times between cases
        thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='arrival', 'time'].values[0]
        inter_arrival_time = thiscase_arrival_time - lastcase_arrival_time
        inter_arrival_times.append(inter_arrival_time)
        print(file = fcasedata)
        print('time between arrivals (this case minus previous case):',inter_arrival_time, 'seconds', file = fcasedata)
        lastcase_arrival_time  = thiscase_arrival_time # save for next case in the for-loop
        # compute waiting times within this case (must have begin_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='begin_service'].shape[0] == 1:
            thiscase_begin_service = thiscase_events.loc[thiscase_events['activity']=='begin_service', 'time'].values[0]
            thiscase_join_queue = thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='join_queue', 'time'].values[0]
            thiscase_waiting_time = thiscase_begin_service - thiscase_join_queue
            waiting_time.append(thiscase_waiting_time)
            print('waiting time for this case (time between joining queue and beginning service):',thiscase_waiting_time, 'seconds', file = fcasedata)
        # compute service time within this case (must have end_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='end_service'].shape[0] == 1:
            thiscase_end_service = thiscase_events.loc[thiscase_events['activity']=='end_service', 'time'].values[0]
            thiscase_service_time = thiscase_end_service - thiscase_begin_service
            service_time.append(thiscase_service_time)
            print('service time for this case (time between beginning and ending service):',thiscase_service_time, 'seconds', file = fcasedata)
        
print()     
print('Summary statistics for customer inter-arrival times:')
print('  Minimum: ',round(np.min(inter_arrival_times),2), ' seconds (' ,round(np.min(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(inter_arrival_times),2), ' seconds (' ,round(np.average(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(inter_arrival_times),2), ' seconds (' ,round(np.max(inter_arrival_times)/60,2), ' minutes)',sep='')      
print()
print('Summary statistics for customer wait times:')
print('  Minimum: ',round(np.min(waiting_time),2), ' seconds (' ,round(np.min(waiting_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(waiting_time),2), ' seconds (' ,round(np.average(waiting_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(waiting_time),2), ' seconds (' ,round(np.max(waiting_time)/60,2), ' minutes)',sep='')  
print()
print('Summary statistics for service times:')
print('  Minimum: ',round(np.min(service_time),2), ' seconds (' ,round(np.min(service_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(service_time),2), ' seconds (' ,round(np.average(service_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(service_time),2), ' seconds (' ,round(np.max(service_time)/60,2), ' minutes)',sep='')  


print()        
print('simulation case-by-case event data written to file:',case_by_case_event_file_name)
print("this log is most useful in checking the logic of the simulation")

# Define output_table data frame for use within KNIME
# KNIME is a low-code platform for data science
output_string_key = []
output_string_value = []

output_string_key.append("Minimum inter-arrival_time")
output_string_value.append(str(round(np.min(inter_arrival_times),2)))
output_string_key.append("Average inter-arrival_time")
output_string_value.append(str(round(np.average(inter_arrival_times),2)))
output_string_key.append("Maximum inter-arrival_time")
output_string_value.append(str(round(np.max(inter_arrival_times),2)))

output_string_key.append("Mimimum waiting time")
output_string_value.append(str(round(np.min(waiting_time),2)))
output_string_key.append("Average waiting time")
output_string_value.append(str(round(np.average(waiting_time),2)))
output_string_key.append("Maximum waiting time")
output_string_value.append(str(round(np.max(waiting_time),2)))

output_string_key.append("Mimimum service time")
output_string_value.append(str(round(np.min(service_time),2)))
output_string_key.append("Average service time")
output_string_value.append(str(round(np.average(service_time),2)))
output_string_key.append("Maximum service time")
output_string_value.append(str(round(np.max(service_time),2)))

output_table = pd.DataFrame({"key":output_string_key, "value":output_string_value})
output_table.set_index(['key'])
