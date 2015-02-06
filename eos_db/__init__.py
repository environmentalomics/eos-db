from pyramid.config import Configurator
from pyramid.events import NewRequest
import logging

ALLOWED_ORIGIN = ('http://localhost:6542', )

def add_cors_headers_response_callback(event):

    def cors_headers(request, response):
        log = logging.getLogger(__name__)
        if 'Origin' in request.headers:
            origin = request.headers['Origin']
            if origin in ALLOWED_ORIGIN:
                log.debug('Access Allowed')
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                
    event.request.add_response_callback(cors_headers)

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.add_subscriber(add_cors_headers_response_callback, NewRequest)
            
    # Top-level home page. Yields API call list?
    
    config.add_route('home', '/')
    
    # Session API calls
    
    config.add_route('sessions', '/sessions') # Get session list
    config.add_route('session', '/session') # Get session details or 
                                            # Post new session or 
                                            # Delete session
        
    # User-related API calls
    
    config.add_route('users', '/users') # Return user list
    config.add_route('user', '/users/{name}')   # Get user details or
                                                        # Post new user or
                                                        # Delete user
                                                        
    config.add_route('user_touches', '/users/{name}/touches') 
                                            # Get server touches
                                            
    config.add_route('user_password', '/users/{name}/password') 
                                            # Put new password
                                            # Get password verification
                                            
    config.add_route('user_credit', '/users/{name}/credit')
                                            # Put new credit or debit
                                            # Get current balance
        
    # Server-related API calls
    
    config.add_route('servers', '/servers') # Return server list
    config.add_route('server', '/servers/{name}')    # Get server details or
                                                    # Post new server or
                                                    # Delete server
    
    config.add_route('states', '/states/{name}') # Get list of servers in given state.
    
    config.add_route('server_start', '/servers/{name}/start')
    config.add_route('server_stop', '/servers/{name}/stop')
    config.add_route('server_suspend', '/servers/{name}/suspend')
    
    config.add_route('server_owner', '/servers/{name}/owner')
    config.add_route('server_touches', '/servers/{name}/touches') 
    config.add_route('server_job_status', '/servers/{name}/job/{job}/status')                                        # Get server touches
                 
    config.scan()
    return config.make_wsgi_app()