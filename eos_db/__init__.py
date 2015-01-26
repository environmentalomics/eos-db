from pyramid.config import Configurator

def main(global_config, **settings):
    config = Configurator(settings=settings)
            
    # Top-level home page. Yields API call list?
    
    config.add_route('home', '/')
    
    # Session API calls
    
    config.add_route('sessions', '/sessions') # Get session list
    config.add_route('session', '/session') # Get session details or 
                                            # Post new session or 
                                            # Delete session
        
    # User-related API calls
    
    config.add_route('users', '/users') # Return user list
    config.add_route('user', '/user/{name}')    # Get user details or
                                                # Post new user or
                                                # Delete user 
    config.add_route('user_touches', '/user/{name}/touches') 
                                            # Get server touches
    config.add_route('user_password', '/user/{name}/password') 
                                            # Put new password
                                            # Get password verification
    config.add_route('user_credit', '/user/{name}/credit')
                                            # Put new credit or debit
                                            # Get current balance
        
    # Server-related API calls
    
    config.add_route('servers', '/servers') # Return server list
    config.add_route('server', '/server/{name}')    # Get server details or
                                                    # Post new server or
                                                    # Delete server
    config.add_route('server_owner', '/server/{name}/owner')
    config.add_route('server_touches', '/server/{name}/touches') 
                                            # Get server touches
            
    config.scan()
    return config.make_wsgi_app()