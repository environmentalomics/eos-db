""" This is an example settings file. If no DBDetails is found a connection
    as the current user will be attempted without a password to the eos_db database.
    If the username is empty the host and password will be ignored but the specified
    database will still be used.
"""

class DBDetails():
    database = 'eos_db'
    username = 'databasedude'
    #These are ignored if username is blank
    password = 'god'
    host     = 'localhost'

""" This structure captures the valid Boost levels for the system.
    It should be edited depending on what you can actually run.
"""
class BoostLevels():

    """Baseline state for machines.
       Not sure if we actually need this or not?
    """
    baseline = { 'label' : 'Standard',
                 'ram'   : '16',
                 'cores' : '1',
                 'cost'  :  0  }

    """Levels in order.  Ideally he portal should fetch this list from a public API call.
       In any case the validity of a boost request should be checked against this table"""
    levels = (
        { 'label'  : 'Standard+',
          'ram'    : '40',
          'cores'  : '2',
          'cost'   :  1           },
        { 'label'  : 'Large',
          'ram'    : '140',
          'cores'  : '8',
          'cost'   :  3           },
        { 'label'  : 'Max',
          'ram'    : '400',
          'cores'  : '16',
          'cost'   :  12          },
    )

    """Capacity table, as determined by abowery.  Each tuple is
        ( state[0].max, state[1].max, state[2].max, ... )
        The number of machines in the baseline state is not checked,
        but on the EOS cloud we assume we can start 20 in total.
    """
    capacity = (
        ( 20,  0,  0 ),
        ( 19,  1,  0 ),
        ( 17,  2,  0 ),
        ( 12,  3,  0 ),
        (  6,  4,  0 ),
        (  0,  5,  0 ),
        ( 10,  0,  1 ),
        (  5,  1,  1 ),
    )

""" Valid extra states that machines can be put into.  Some states are special and
    necessary to the operation of eos-db while others are opaque and only of interest to
    the agents.
    See https://drive.google.com/file/d/0B6tR3eRvaksUUnhzLVBfR3J1dW8/view?usp=sharing
"""
# class MachineStates():
#     state_list = ( 'State1', 'State2' )

