"""
Script to backup and restore jenkins jobs, plugins and configuration

"""
import sys,os,requests,argparse,shutil,json,zipfile,xml.etree.ElementTree as ET,tempfile,time

#list jenkins Api endpoints
# /api/json - Returns JSON data describing the Jenkins instance.

# /view/{view-name}/api/json - Returns JSON data for a specific view.

# /job/{job-name}/api/json - Returns JSON data for a specific job.

# /job/{job-name}/lastBuild/api/json - Returns JSON data for the last build of a specific job.

# /job/{job-name}/{build-number}/api/json - Returns JSON data for a specific build of a specific job.

# /job/{job-name}/{build-number}/logText/progressiveText - Returns the console output (log) for a specific build of a specific job, as a plain text stream.

# /job/{job-name}/{build-number}/logText/progressiveHtml - Returns the console output (log) for a specific build of a specific job, as an HTML stream.

# /job/{job-name}/{build-number}/logText/{start}/{end}/log.gz - Returns a compressed log file for a specific range of the console output (log) of a specific build of a specific job.

# /queue/api/json - Returns JSON data for the build queue.

# /computer/api/json - Returns JSON data for all Jenkins nodes (agents).

# /computer/{node-name}/api/json - Returns JSON data for a specific Jenkins node (agent).

# /user/{username}/api/json - Returns JSON data for a specific user.

# /crumbIssuer/api/json - Returns JSON data for the CSRF protection crumb issuer.

# /pluginManager/api/json - Returns JSON data for all Jenkins plugins.

# /pluginManager/api/xml - Returns XML data for all Jenkins plugins.

class MyJenkins():
    """
    Class to backup and restore jenkins jobs, plugins and configuration
    """
    def __init__(self, args):

        self.loggers=False
        if "-l" in sys.argv or "--log" in args:
            self.loggers=True 
        if args.url is None:
            self.url = 'http://localhost:8080'
        else:
            self.url = args.url
        if args.username is None:
            self.username = 'admin'
        else:
            self.username = args.username
        if args.token is None:
            self.token = 'admin'
        else:
            self.token = args.token
        if args.backup_dir is None:
            self.backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')
        else:
            self.backup_dir = args.backup_dir
        if args.restore_dir is None:
            self.restore_dir = self.backup_dir
        else:
            self.restore_dir = args.restore_dir
        if args.zip_dir is None:
            self.zip_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zip')
            print(self.zip_dir)
        else:
            self.zip_dir = args.zip_dir
        if args.zip is None:
            self.zip_file = os.path.join(self.zip_dir, 'backup.zip') 
        else:
            self.zip_file = os.path.join(self.zip_dir, args.zip)
        self.session = requests.Session()
        self.session.auth = (self.username, self.token)
        self.session.headers.update({'Content-Type':'text/xml'})
        self.session.verify = False
        self.session.stream = True
        self.session.timeout = 30
        
        self.folder_dir=self.backup_dir+'/folder'
        self.folder_jobs_dir = self.folder_dir + '/jobs'
        self.jobs_dir = self.backup_dir + '/jobs'
        self.plugins_dir = self.backup_dir + '/plugins'
        self.views_dir = self.backup_dir + '/views'
        self.nodes_dir = self.backup_dir + '/nodes'
        self.config_dir = self.backup_dir + '/config'
        self.log_dir = self.backup_dir + '/log'
        self.jobs_log_dir=self.jobs_dir+'/log'
        self.plugins_log_dir=self.plugins_dir+'/log'
        self.views_log_dir=self.views_dir+'/log'
        self.nodes_log_dir=self.nodes_dir+'/log'
        self.folder_jobs_log_dir=self.folder_jobs_dir+'/log'

    def get_job(self, job_name):
        """
        Get job
        """
        job = None
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/api/json')
            job = response.json()
        except:
            pass
        return job
    def get_node(self, node_name):
        """
        Get node
        """
        node = None
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/api/json')
            node = response.json()
        except:
            pass
        return node
    def get_view(self, view_name):
        """
        Get view
        """
        view = None
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/api/json')
            view = response.json()
        except:
            pass
        return view

    def read_json_file(self, file_name, parentkey):
        
        """
        Read json file
        """
        try:
            with open(file_name, 'r') as json_file:
                json_data = json.load(json_file)
            return json_data[parentkey]
        except:
            return None
    
    def write_json_file(self, file_name,parentkey, key, value):
        """
        Write json file
        """
        json_data=None
        if not os.path.exists(file_name) or os.stat(file_name).st_size == 0:
            with open(file_name, 'w') as json_file:
                json.dump({}, json_file)
        else:
            try:        
                with open(file_name, 'r') as json_file:
                    json_data = json.load(json_file)
                json_data[parentkey][key]=value
            except:
                json_data[parentkey]={}
                json_data[parentkey][key]=value
            finally:
                with open(file_name, 'w') as json_file:
                    json.dump(json_data, json_file) 

    def remove_all_files_in_dir(self, dir_name):
        """
        Remove all files in directory
        """
        if not os.path.exists(dir_name):
            return False
        elif not os.path.isdir(dir_name):
            return False
        elif not os.listdir(dir_name):
            os.rmdir(dir_name)
            return True
        for file_name in os.listdir(dir_name):
            try:
                # check if file is djrectory and empty
                if os.path.isdir(os.path.join(dir_name, file_name)) and not os.listdir(os.path.join(dir_name, file_name)):
                    os.rmdir(os.path.join(dir_name, file_name))
                # check if file is a file
                elif os.path.isfile(os.path.join(dir_name, file_name)):
                    os.remove(os.path.join(dir_name, file_name))
                #check if file is a directory 
                if os.path.isdir(os.path.join(dir_name, file_name)):
                    self.remove_all_files_in_dir(os.path.join(dir_name, file_name))
                    os.rmdir(os.path.join(dir_name, file_name))   
                #check if file is a symbolic link
                if os.path.islink(os.path.join(dir_name, file_name)):
                    os.remove(os.path.join(dir_name, file_name))
                #check if file is a mount point
                if os.path.ismount(os.path.join(dir_name, file_name)):
                    os.remove(os.path.join(dir_name, file_name))
            except:
                pass
        if not os.listdir(dir_name):
            try:
                os.rmdir(dir_name)
            except:
                pass
            return True
        else:     
            return False

    def get_all_nodes(self):
        """
        Get all nodes
        """
        nodes = []
        try:
            response = self.session.get(self.url + '/computer/api/json')
            nodes = response.json()['computer']
        except:
            pass
        return nodes

    def get_all_views(self):
        """
        Get all views
        """
        views = []
        try:
            response = self.session.get(self.url + '/view/api/json')
            views = response.json()['views']
        except:
            pass
        return views

    def get_plugin_list(self):
        """
        Get all plugins
        """
        plugins = []
        try:
            response = self.session.get(self.url + '/pluginManager/api/json')
            plugins = response.json()['plugins']
        except:
            pass
        return plugins

    def compress_all_files_in_dir(self,zip_file_name,dir_name):
        """
        Compress all files in to a zip file relative to dir_name and remove full directory path
        """

        #check if directory exists
        if not os.path.exists(dir_name):
            #create directory
            os.makedirs(dir_name)
        try:
            zip_file = zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED)
            for root, dirs, files in os.walk(dir_name):
                for file in files:
                    zip_file.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(dir_name, '..')))
            zip_file.close()
        except Exception as e:
            print(e)
            pass

    def decompress_all_files_in_dir(self, zip_file_name, dir_name=None):
        """
        Decompress all files in a directory
        """
        getparentdir = os.path.dirname(os.path.dirname(zip_file_name))
        try:
            zip_file = zipfile.ZipFile(zip_file_name, 'r')
            if dir_name is None:
                dir_name = os.path.splitext(zip_file_name)[0]
            zip_file.extractall(getparentdir)
            zip_file.close()
        except:
            pass

    def delete_all_directory_after_compressed(self, dir_name):
        """
        Delete all directory after compressed
        """
        try:
            shutil.rmtree(dir_name)
            return True
        except:
            return False

    def create_dir(self, dir_name):
        """
        Create directory
        """
        try:
            os.mkdir(dir_name)
        except:
            pass

    def create_backup_dir(self): 
        """
        Create backup directory
        """
        
        self.folder_dir=self.backup_dir+'/folder'
        self.folder_jobs_dir = self.folder_dir + '/jobs'
        self.jobs_dir = self.backup_dir + '/jobs'
        self.plugins_dir = self.backup_dir + '/plugins'
        self.views_dir = self.backup_dir + '/views'
        self.nodes_dir = self.backup_dir + '/nodes'
        self.config_dir = self.backup_dir + '/config'
        self.log_dir = self.backup_dir + '/log'
        self.jobs_log_dir=self.jobs_dir+'/log'
        self.plugins_log_dir=self.plugins_dir+'/log'
        self.views_log_dir=self.views_dir+'/log'
        self.nodes_log_dir=self.nodes_dir+'/log'
        self.folder_jobs_log_dir=self.folder_jobs_dir+'/log'

        self.create_dir(self.backup_dir)
        self.create_dir(self.zip_dir)
        self.create_dir(self.jobs_dir)
        self.create_dir(self.plugins_dir)
        self.create_dir(self.views_dir)
        self.create_dir(self.nodes_dir)
        self.create_dir(self.config_dir)
        self.create_dir(self.log_dir)
        self.create_dir(self.folder_dir)
        self.create_dir(self.folder_jobs_dir)
        self.create_dir(self.jobs_log_dir)
        self.create_dir(self.plugins_log_dir)
        self.create_dir(self.views_log_dir)
        self.create_dir(self.nodes_log_dir)
        self.create_dir(self.folder_jobs_log_dir)


    def delete_backup_dir(self):
        """
        Delete backup directory
        """
        self.remove_all_files_in_dir(self.backup_dir)
    def get_view_list(self):
        """
        Get view list
        """
        try:
            r = self.session.get(self.url + '/api/json?tree=views[name]')
            return r.json()['views']
        except:
            return False
    
    def get_node_list(self):
        """
        Get node list
        """
        try:
            r = self.session.get(self.url + '/computer/api/json?tree=computer[displayName]')
            return r.json()['computer']
        except:
            return False
        
    def get_node_config(self, node_name):
        """
        Get node config
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/config.xml')
            return response.text
        except:
            return None
    
    def get_node_last_build(self, node_name):
        """
        Get node last build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_last_completed_build(self, node_name):
        """
        Get node last completed build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastCompletedBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_last_failed_build(self, node_name):
        """
        Get node last failed build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastFailedBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_last_stable_build(self, node_name):
        """
        Get node last stable build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastStableBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_last_successful_build(self, node_name):
        """
        Get node last successful build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastSuccessfulBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_last_unstable_build(self, node_name):
        """
        Get node last unstable build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastUnstableBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_last_unsuccessful_build(self, node_name):
        """
        Get node last unsuccessful build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/lastUnsuccessfulBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_node_build(self, node_name, build_number=None):
        if build_number==None:
            build_number=self.get_node_build_number(node_name)
        """
        Get node build
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/' + str(build_number) + '/api/json')
            return response.json()
        except:
            return None
    
    def get_node_build_config(self, node_name, build_number=None):
        if build_number==None:
            build_number=self.get_node_build_number(node_name)
        """
        Get node build config
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/' + str(build_number) + '/config.xml')
            return response.text
        except:
            return None
    
    def get_node_build_console(self, node_name, build_number=None):
        if build_number==None:
            build_number=self.get_node_last_build_number(node_name)
        """
        Get node build console
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/' + str(build_number) + '/consoleText')
            return response.text
        except:
            return None
    
    def get_node_build_log(self, node_name, build_number=None):
        if build_number==None:
            build_number=self.get_node_build_number(node_name)
        """
        Get node build log
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/' + str(build_number) + '/logText/progressiveText')
            return response.text
        except:
            return None

    def get_nodes(self):
        """
        Get all nodes
        """
        nodes = []
        try:
            response = self.session.get(self.url + '/computer/api/json')
            nodes = response.json()['computer']
        except:
            pass
        return nodes

    def backup_view_build_log(self, view_name, build_number=None):
        if build_number==None:
            build_number=self.get_view_build_number(view_name)
        """
        Backup view build log
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/' + str(build_number) + '/logText/progressiveText')
            file_to_write = open(self.views_log_dir+view_name + str(build_number) + '.txt', 'w')
            file_to_write.write(response.text)
            file_to_write.close()
            file_to_write = open(self.views_log_dir+view_name + str(build_number) + '.xml', 'w')
            file_to_write.write(response.text)
            file_to_write.close()
            return True
        except:
            return False
    
    def backup_node_build_log(self, node_name, build_number=None):
        if build_number==None:
            build_number=self.get_node_build_number(node_name)
        """
        Backup node build log
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/' + str(build_number) + '/logText/progressiveText')
            file_to_write = open(self.nodes_log_dir+node_name + str(build_number) + '.txt', 'w')
            file_to_write.write(response.text)
            file_to_write.close()
            file_to_write = open(self.nodes_log_dir+node_name + str(build_number) + '.xml', 'w')
            file_to_write.write(response.text)
            file_to_write.close()
            return True
        except:
            return False
    def restore_node_build_log(self, node_name, build_number=None):
        if build_number==None:
            build_number=self.get_node_build_number(node_name)
        """
        Restore node build log
        """
        try:
            file_to_read = open(self.nodes_log_dir+node_name + str(build_number) + '.xml', 'r').read()
            response = self.session.post(self.url + '/computer/' + node_name + '/' + str(build_number) + '/logText/progressiveText', data=file_to_read)
            return True
        except:
            return False
    def get_file_content(self, file_path):
        """
        Get file content
        """
        file_to_read = None
        if file_path is None:
            return None
        else:  
            try:
                file_to_read = open(file_path, 'r').read()  
                return file_to_read
            except:
                return None

    def get_view_config(self, view_name):
        """
        Get view config
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/config.xml')
            return response.text
        except:
            return None
    
    def get_views(self):
        """
        Get all views
        """
        views = []
        try:
            response = self.session.get(self.url + '/view/all/api/json')
            views = response.json()['views']
        except:
            pass
        return views
    def get_job_build_console(self, job_name, build_number=None):
        if build_number==None:
            build_number=self.get_job_build_number(job_name)
        """
        Get job build console
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/' + str(build_number) + '/consoleText')
            return response.text
        except:
            return None
    
    def get_jobs(self, folder_dir=None):
        """
        Get all jobs
        """
        jobs = []
        try:
            response = self.session.get(self.url + '/api/json')
            jobs = response.json()['jobs']
        except:
            # Read from directory
            if folder_dir is not None:
                #get jobs from folder
                for file in os.listdir(self.jobs_dir):
                    if file.endswith(".xml"):
                        jobs.append({'name': file.split('.')[0]})
        return jobs
    def get_job_config(self, job_name):
        """
        Get job config
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/config.xml')
            return response.text
        except:
            return None
    
    def get_job_last_build(self, job_name):
        """
        Get job last build
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/lastBuild/api/json')
            return response.json()
        except:
            return None
    
    def get_logs(self):
        """
        Get all logs
        """
        logs = []
        try:
            response = self.session.get(self.url + '/queue/api/json')
            logs = response.json()['items']
        except:
            pass
        return logs
    def get_log(self, log_id):
        """
        Get log
        """
        try:
            response = self.session.get(self.url + '/queue/item/' + str(log_id) + '/api/json')
            return response.json()
        except:
            return None
    
    def get_view_build_log(self, view_name, build_number=None):
        if build_number==None:
            build_number=self.get_view_build_number(view_name)
        """
        Get view build log
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/' + str(build_number) + '/logText/progressiveText')
            return response.text
        except:
            return None 
    def get_view_build_console(self, view_name, build_number=None):
        if build_number==None:
            build_number=self.get_view_build_number(view_name)
        """
        Get view build console
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/' + str(build_number) + '/consoleText')
            return response.text
        except:
            return None
    
    def get_view_build(self, view_name, build_number=None):
        if build_number==None:
            build_number=self.get_View_build_number(view_name)
        """
        Get view build
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/' + str(build_number) + '/api/json')
            return response.json()
        except:
            return None
    
    def get_view_build_config(self, view_name, build_number=None):
        if build_number==None:
            build_number=self.get_view_build_number(view_name)
        """
        Get view build config
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/' + str(build_number) + '/config.xml')
            return response.text
        except:
            return None
    
    def get_job_build_log(self, job_name, build_number=None):
        if build_number==None:
            build_number=self.get_job_build_number(job_name)

        """
        Get job build log
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/' + str(build_number) + '/logText/progressiveText')
            return response.text
        except:
            return None
    
    def get_node_log(self, node_name, log_id):
        """
        Get node log
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/queue/item/' + str(log_id) + '/api/json')
            return response.json()
        except:
            return None
    
    def get_node_logs(self, node_name):
        """
        Get node logs
        """
        logs = []
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/queue/api/json')
            logs = response.json()['items']
        except:
            pass
        return logs
    def get_View_build_number(self, view_name):
        """
        Get view build number
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None
    
    def get_job_build_number(self, job_name):
        """
        Get job build number
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None

    def get_plugin_build_number(self, plugin_name):
        """
        Get plugin build number
        """
        try:
            response = self.session.get(self.url + '/plugin/' + plugin_name + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None

    def get_plugin_build(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Get plugin build
        """
        try:
            response = self.session.get(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/api/json')
            return response.json()
        except:
            return None
    
    def get_plugin_build_log(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Get plugin build log
        """
        try:
            response = self.session.get(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/logText/progressiveText')
            return response.text
        except:
            return None

    def backup_plugin_build_log(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Backup plugin build log
        """
        try:
            #response = self.session.get(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/logText/progressiveText')
            with open(self.plugins_log_dir+plugin_name + str(build_number) + '.log', 'w') as f:
                f.write(self.get_plugin_build_log(plugin_name))
            with open(self.plugins_log_dir+plugin_name + str(build_number) + '.xml', 'w') as f:
                f.write(self.get_plugin_build_log(plugin_name))    
            return True
        except:
            return False
    def backup_plugin_build_config(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Backup plugin build config
        """
        try:
            #response = self.session.get(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/config.xml')
            with open(self.plugins_log_dir+plugin_name + str(build_number) + '.xml', 'w') as f:
                f.write(self.get_plugin_build_config(plugin_name))
            #write to json file
            self.write_json_file("details.json","Plugins",plugin_name, self.plugins_log_dir+plugin_name + str(build_number) + '.xml')
            return True
        except:
            return False   

    def restore_plugin_build_log(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Restore plugin build log
        """
        try:
            with open(self.plugins_log_dir+plugin_name + str(build_number) + '.xml', 'r') as f:
                log = f.read()
            response = self.session.post(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/logText/progressiveText', data=log)
            return True
        except:
            return False
        
    def get_plugin_build_console(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Get plugin build console
        """
        try:
            response = self.session.get(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/consoleText')
            return response.text
        except:
            return None

    def get_plugin_build_config(self, plugin_name, build_number=None):
        if build_number==None:
            build_number=self.get_plugin_build_number(plugin_name)
        """
        Get plugin build config
        """
        try:
            response = self.session.get(self.url + '/plugin/' + plugin_name + '/' + str(build_number) + '/config.xml')
            return response.text
        except:
            return None

    def get_folder_build_number(self, folder_name):
        """
        Get folder build number
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None

    def get_node_build_number(self, node_name):
        """
        Get node build number
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None

    def get_folder_job_build_number(self, folder_name, job_name):
        """
        Get folder job build number
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/job/' + job_name + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None

    def get_config_build_number(self):
        """
        Get config build number
        """
        try:
            response = self.session.get(self.url + '/api/json')
            return response.json()['lastBuild']['number']
        except:
            return None

    def get_plugins(self):
        """
        Get all plugins
        """
        plugins = []
        try:
            response = self.session.get(self.url + '/pluginManager/api/json')
            plugins = response.json()['plugins']
        except:
            pass
        return plugins

    def get_plugin_config(self, plugin_name):
        """
        Get plugin config
        """
        try:
            response = self.session.get(self.url + '/pluginManager/plugin/' + plugin_name + '/config.xml')
            return response.text
        except:
            return None

    def get_config(self):
        """
        Get config
        """
        try:
            response = self.session.get(self.url + '/config.xml')
            return response.text
        except:
            return None

    def get_jobs_by_folder(self, folder_name):
        """
        Get jobs by folder
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/api/json')
            return response.json()['jobs']
        except:
            return False

    def get_folder_config(self, folder_name):
        """
        Get folder config
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/config.xml')
            return response.text
        except:
            return None

    def get_folder_last_build(self, folder_name):
        """
        Get folder last build
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/lastBuild/api/json')
            return response.json()
        except:
            return None

    def get_folder_build_log(self, folder_name, build_number=None):
        if build_number==None:
            build_number=self.get_folder_build_number(folder_name)
        """
        Get folder build log
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/' + str(build_number) + '/logText/progressiveText')
            return response.text
        except:
            return None

    def get_folders(self):
        """
        Get all folders
        """
        folders = []
        try:
            response = self.session.get(self.url + '/api/json')
            for job in response.json()['jobs']:
                try:
                    if job['_class'] == 'com.cloudbees.hudson.plugins.folder.Folder':
                        folders.append(job)
                except:
                    try:
                        if 'jobs' in job:
                            folders.append(job)
                    except:
                        pass
        except:
            pass
        return folders

    def get_folder_jobs(self, folder_name):
        """
        Get folder jobs
        """
        jobs = []
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/api/json')
            jobs = response.json()['jobs']
        except:
            pass
        return jobs
    
    def get_node_config(self, node_name):
        """
        Get node config
        """
        try:
            response = self.session.get(self.url + '/computer/' + node_name + '/config.xml')
            return response.text
        except:
            return None    

    def get_folder_job_config(self, folder_name, job_name):
        """
        Get folder job config
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/job/' + job_name + '/config.xml')
            return response.text
        except:
            return None

    def get_folder_job_last_build(self, folder_name, job_name):
        """
        Get folder job last build
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/job/' + job_name + '/lastBuild/api/json')
            return response.json()
        except:
            return None

    def get_folder_job_build_log(self, folder_name, job_name, build_number=None):
        if build_number==None:
            build_number=self.get_folder_job_build_number(folder_name, job_name)
        """
        Get folder job build log
        """
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/job/' + job_name + '/' + str(build_number) + '/logText/progressiveText')
            return response.text
        except:
            return None
    
    def backup_folder_build_log(self, folder_name, build_number=None):
        if build_number==None:
            build_number=self.get_folder_build_number(folder_name)
        """
        Backup folder build log
        """
        try:
            log = self.get_folder_build_log(folder_name, build_number)
            with open(self.folder_log_dir+folder_name + str(build_number) + '.log', 'w') as f:
                f.write(log)
            with open(self.folder_log_dir+folder_name + str(build_number) + '.xml', 'w') as f:
                f.write(log)  
            self.write_json_file("details.json","Folders",folder_name, self.folder_log_dir+folder_name + str(build_number) + '.xml')  
            return True
        except:
            return False
    
    def get_folder_job_builds(self, folder_name, job_name):
        """
        Get folder job builds
        """
        builds = []
        try:
            response = self.session.get(self.url + '/job/' + folder_name + '/job/' + job_name + '/api/json')
            builds = response.json()['builds']
        except:
            pass
        return builds
   
    def create_job(self, job_name):
        """
        Create job
        """
        try:
            with open(os.path.join(self.jobs_dir, job_name + '.xml'), 'r') as f:
                job_config = f.read()
            response = self.session.post(f"{self.url}/createItem?name={job_name}", data=job_config)
            print(response.status_code)
            return True
        except Exception as e:
            print(e)
            return False
    
    def create_config(self, config_name):
        """
        Create config
        """
        try:
            with open(os.path.join(self.config_dir, f'{config_name}.xml'), 'r') as f:
                config_config = f.read()
            self.session.post(self.url + '/config.xml', data=config_config)
            return True
        except:
            return False
    
    def create_plugin(self, plugin_name):
        """
        Create plugin
        """
        with open(os.path.join(self.plugins_dir, f'{plugin_name}.xml'), 'r') as f:
            plugin_config = f.read()
        try:
            self.session.post(self.url + '/pluginManager/installNecessaryPlugins', data=plugin_config)
            return True
        except:
            return False
    
    def create_view(self, view_name):
        """
        Create view
        """
        with open(os.path.join(self.views_dir, f'{view_name}.xml'), 'r') as f:
            view_config = f.read()
        try:
            self.session.post(self.url + '/createView?name=' + view_name, data=view_config)
            return True
        except:
            return False
    
    def create_node(self, node_name):
        """
        Create node
        """
        with open(os.path.join(self.nodes_dir, f'{node_name}.xml'), 'r') as f:
            node_config = f.read()
        try:
            self.session.post(self.url + '/computer/doCreateItem?name=' + node_name, data=node_config)
            return True
        except:
            return False
    
    def create_folder(self, folder_name):
        """
        Create folder
        """
        with open(os.path.join(self.folders_dir, f'{folder_name}.xml'), 'r') as f:
            folder_config = f.read()
        try:
            self.session.post(self.url + '/createItem?name=' + folder_name, data=folder_config)
            return True
        except:
            return False
    
    def create_folder_job(self, folder_name, job_name):
        """
        Create folder job
        """
        with open(os.path.join(self.folder_jobs_dir, f'{job_name}.xml'), 'r') as f:
            job_config = f.read()
        try:
            self.session.post(self.url + '/job/' + folder_name + '/createItem?name=' + job_name, data=job_config)
            return True
        except:
            return False
    
    def create_folder_view(self, folder_name, view_name):
        """
        Create folder view
        """
        with open(os.path.join(self.folder_views_dir, f'{view_name}.xml'), 'r') as f:
            view_config = f.read()
        try:
            self.session.post(self.url + '/job/' + folder_name + '/createView?name=' + view_name, data=view_config)
            return True
        except:
            return False
    
    def create_folder_node(self, folder_name, node_name):
        """
        Create folder node
        """
        with open(os.path.join(self.folder_nodes_dir, f'{node_name}.xml'), 'r') as f:
            node_config = f.read()
        try:
            self.session.post(self.url + '/job/' + folder_name + '/computer/doCreateItem?name=' + node_name, data=node_config)
            return True
        except:
            return False
    
    def remove_job(self, job_name):
        """
        Remove job
        """
        try:
            self.session.post(self.url + '/job/' + job_name + '/doDelete')
            return True
        except:
            return False
    
    def remove_plugin(self, plugin_name):
        """
        Remove plugin
        """
        try:
            self.session.post(self.url + '/pluginManager/plugin/' + plugin_name + '/doUninstall')
            return True
        except:
            return False
    
    def remove_view(self, view_name):
        """
        Remove view
        """
        try:
            self.session.post(self.url + '/view/' + view_name + '/doDelete')
            return True
        except:
            return False
    
    def remove_node(self, node_name):
        """
        Remove node
        """
        try:
            self.session.post(self.url + '/computer/' + node_name + '/doDelete')
            return True
        except:
            return False
    
    def remove_config(self):
        """
        Remove config
        """
        try:
            self.session.post(self.url + '/configureSecurity')
            return True
        except:
            return False
    
    def remove_folder(self, folder_name):
        """
        Remove folder
        """
        try:
            self.session.post(self.url + '/job/' + folder_name + '/doDelete')
            return True
        except:
            return False
    
    def remove_folder_job(self, folder_name, job_name):
        """
        Remove folder job
        """
        try:
            self.session.post(self.url + '/job/' + folder_name + '/job/' + job_name + '/doDelete')
            return True
        except:
            return False
    
    def remove_folder_view(self, folder_name, view_name):
        """
        Remove folder view
        """
        try:
            self.session.post(self.url + '/job/' + folder_name + '/view/' + view_name + '/doDelete')
            return True
        except:
            return False
    
    def remove_folder_node(self, folder_name, node_name):
        """
        Remove folder node
        """
        try:
            self.session.post(self.url + '/job/' + folder_name + '/computer/' + node_name + '/doDelete')
            return True
        except:
            return False
    

    def backup(self, backup_dir):
        """
        Backup jobs, plugins and config
        """
        self.backup_dir = backup_dir
        self.jobs_dir = os.path.join(self.backup_dir, 'jobs')
        self.plugins_dir = os.path.join(self.backup_dir, 'plugins')
        self.views_dir = os.path.join(self.backup_dir, 'views')
        self.nodes_dir = os.path.join(self.backup_dir, 'nodes')
        self.zip_dir = os.path.join(self.backup_dir, 'zip')
        self.zip = os.path.join(self.zip_dir, 'backup.zip')
        self.config_dir = os.path.join(self.backup_dir, 'config')

        
        self.create_dir(self.backup_dir)
        self.create_dir(self.jobs_dir)
        self.create_dir(self.plugins_dir)
        self.create_dir(self.views_dir)
        self.create_dir(self.nodes_dir)
        self.create_dir(self.zip_dir)
        self.create_dir(self.config_dir)
        try:
            jobs = self.get_jobs()
            for job in jobs:
                job_name = job['name']

                job_config = self.get_job_config(job_name)
                
                if job_config:
                    with open(os.path.join(self.jobs_dir, job_name + '.xml'), 'w') as job_file:
                        job_file.write(job_config)
                    self.write_json_file("details.json","Jobs",job_name,os.path.join(self.jobs_dir, job_name + '.xml'))
                        
                last_build = self.get_job_last_build(job_name)
                if last_build:
                    build_number = last_build['number']

                    build_log = self.get_job_build_log(job_name, build_number)
                    if build_log:
                        with open(os.path.join(self.log_dir, job_name + '.log'), 'w') as job_file:
                            job_file.write(build_log)
                        self.write_json_file("details.json","Builds","{}{}".format(job_name,build_number),os.path.join(self.log_dir, job_name + '.log'))
        except:
            pass
        try:    
            plugins = self.get_plugins()
            for plugin in plugins:
                plugin_name = plugin['shortName']
                plugin_config = self.get_plugin_config(plugin_name)
                if plugin_config:
                    with open(os.path.join(self.plugins_dir, plugin_name + '.xml'), 'w') as plugin_file:
                        plugin_file.write(plugin_config)
                        self.write_json_file("details.json","Plugins",plugin_name,os.path.join(self.plugins_dir, plugin_name + '.xml'))
                    if self.mylogger==True:
                        self.backup_plugin_build_log(plugin_name,self.get_plugin_build_number(plugin_name))
                            
        except:
            pass
        try:
            views = self.get_views()
            for view in views:
                view_name = view['name']
                view_config = self.get_view_config(view_name)
                if view_config:
                    with open(os.path.join(self.views_dir, view_name + '.xml'), 'w') as view_file:
                        view_file.write(view_config)
                        self.write_json_file("details.json","Views",view_name,os.path.join(self.views_dir, view_name + '.xml'))
        except:
            pass
        try:
            nodes = self.get_nodes()
            for node in nodes:
                node_name = node['displayName']
                node_config = self.get_node_config(node_name)
                if node_config:
                    with open(os.path.join(self.nodes_dir, node_name + '.xml'), 'w') as node_file:
                        node_file.write(node_config)
                        self.write_json_file("details.json","Nodes",node_name,os.path.join(self.nodes_dir, node_name + '.xml'))
        except:
            pass                          
        try:
            config = self.get_config()
            if config:
                with open(os.path.join(self.config_dir, 'config.xml'), 'w') as config_file:
                    config_file.write(config)
                    self.write_json_file("details.json","Config","config",os.path.join(self.config_dir, 'config.xml'))
        except:
            pass        
        self.compress_all_files_in_dir(self.zip,self.backup_dir)
        self.remove_all_files_in_dir(self.backup_dir)

    def restore(self, backup_dir=None):

        """
        Restore jobs, plugins and config
        """
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            self.backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')
        self.jobs_dir = os.path.join(self.backup_dir, 'jobs')
        self.folder_dir = os.path.join(self.backup_dir, 'folder')
        self.plugins_dir = os.path.join(self.backup_dir, 'plugins')
        self.views_dir = os.path.join(self.backup_dir, 'views')
        self.nodes_dir = os.path.join(self.backup_dir, 'nodes')
        self.zip_dir = os.path.join(self.backup_dir, 'zip')
        self.zip= os.path.join(self.backup_dir, 'zip.zip')
        self.config_dir = os.path.join(self.backup_dir, 'config')

        #check if backup dir exists
        if not os.path.exists(self.backup_dir):
            self.decompress_all_files_in_dir(self.zip, self.backup_dir)
        
        for job_file in os.listdir(self.jobs_dir):
            job_name = job_file.split('.')[0]
            self.create_job(job_name)
        
        for plugin_file in os.listdir(self.plugins_dir):
            plugin_name = plugin_file.split('.')[0]
            self.create_plugin(plugin_name)
        
        for config_config in os.listdir(self.config_dir):
            config_config = config_config.split('.')[0]
            self.create_config(config_config)
        for folder_file in os.listdir(self.folder_dir):
            folder_name = folder_file.split('.')[0]
            self.create_folder(folder_name)

        for view_file in os.listdir(self.views_dir):
            view_name = view_file.split('.')[0]
            self.create_view(view_name)
        for node_file in os.listdir(self.nodes_dir):
            node_name = node_file.split('.')[0]
            self.create_node(node_name)
        #Remove all files in backup dir
        self.remove_all_files_in_dir(self.backup_dir)
    def create_folder(self, folder_name):
        """
        Create folder
        """
        try:
            self.session.post(self.url + '/createItem?name=' + folder_name)
            return True
        except:
            return False
    
    def delete_folder(self, folder_name):
        """
        Delete folder
        """
        try:
            self.session.post(self.url + '/job/' + folder_name + '/doDelete')
            return True
        except:
            return False
    
    def move_job(self, job_name, folder_name):
        """
        Move job to folder
        """
        try:
            self.session.post(self.url + '/job/' + job_name + '/doMove?newName=' + folder_name + '/' + job_name)
            return True
        except:
            return False
    
    def move_folder(self, folder_name, new_folder_name):
        """
        Move folder to folder
        """
        try:
            self.session.post(self.url + '/job/' + folder_name + '/doMove?newName=' + new_folder_name + '/' + folder_name)
            return True
        except:
            return False
    
    def copy_job(self, job_name, new_job_name):
        """
        Copy job
        """
        try:
            self.session.post(self.url + '/createItem?name=' + new_job_name + '&mode=copy&from=' + job_name)
            return True
        except:
            return False
    
    def copy_folder(self, folder_name, new_folder_name):
        """
        Copy folder
        """
        try:
            self.session.post(self.url + '/createItem?name=' + new_folder_name + '&mode=copy&from=' + folder_name)
            return True
        except:
            return False
    
    def get_job_info(self, job_name):
        """
        Get job info
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/api/json')
            return response.json()
        except:
            return False
    
    def get_job_config(self, job_name):
        """
        Get job config
        """
        try:
            response = self.session.get(self.url + '/job/' + job_name + '/config.xml')
            #print(response.text)
            return response.text
        except:
            return False

    def backup_log(self, job_name, build_number=None):
        if build_number==None:
            build_number=self.get_job_build_number(job_name)
        """
        Backup job build log
        """
        try:
            build_log = self.get_job_build_log(job_name, build_number)
            if build_log:
                with open(os.path.join(self.jobs_log_dir, job_name + '.log'), 'w') as job_file:
                    job_file.write(build_log)
                with open(os.path.join(self.jobs_log_dir, job_name + '.xml'), 'w') as job_file:
                    job_file.write(build_log) 
                self.write_json_file("details.json","JobLogs",job_name, (self.jobs_log_dir, job_name + '.xml'))    
            return True
        except:
            return False
    
    def restore_log(self, job_name,build_number=None,file_path=None):
        """
        Restore job build log
        """
        try:
            if file_path==None:
                with open(os.path.join(self.jobs_dir, job_name + '.xml'), 'r') as job_file:
                    build_log = job_file.read()
                self.create_job_build_log(job_name, build_log)
            else:
                if build_number !=None:
                    job_name
                with open(os.path.join(file_path, job_name + '.xml'), 'r') as job_file:
                    build_log = job_file.read()
                self.create_job_build_log(job_name, build_log)
            return True
        except:
            return False
    
    def get_view_info(self, view_name):
        """
        Get view info
        """
        try:
            response = self.session.get(self.url + '/view/' + view_name + '/api/json')
            return response.json()
        except:
            return False
    
    def backup_view_log(self, view_name, build_number=None):
        if build_number==None:
            build_number=get_view_build_number(view_name)
        """
        Backup view build log
        """
        try:
            build_log = self.get_view_build_log(view_name, build_number)
            if build_log:
                
                with open(os.path.join(self.views_log_dir, view_name + '.log'), 'w') as view_file:
                    view_file.write(build_log)
                with open(os.path.join(self.views_log_dir, view_name + '.xml'), 'w') as view_file:
                    view_file.write(build_log)    
                self.write_json_file("details.json","ViewLogs",view_name, (self.views_log_dir, view_name + '.xml'))    
            return True
        except:
            return False

    def restore_view_log(self, view_name,build_number=None,file_path=None):
        """
        Restore view build log
        """
        try:
            if file_path==None:
                with open(os.path.join(self.views_log_dir, view_name + '.xml'), 'r') as view_file:
                    build_log = view_file.read()
                self.create_view_build_log(view_name, build_log)
            else:
                with open(os.path.join(file_path, view_name + '.xml'), 'r') as view_file:
                    build_log = view_file.read()
                self.create_view_build_log(view_name, build_log)
            return True
        except:
            return False
    def backup_node(self, node_name):
        """
        Backup node
        """
        try:
            node_config = self.get_node_config(node_name)
            if node_config:
                if self.loggers:
                    self.backup_node_build_log(node_name)
                with open(os.path.join(self.nodes_dir, node_name + '.xml'), 'w') as node_file:
                    node_file.write(node_config)
                self.write_json_file("details.json","Nodes",node_name, (self.nodes_dir, node_name + '.xml'))
            return True
        except:
            return False
    
    def restore_node(self, node_name):
        """
        Restore node
        """
        try:
            with open(os.path.join(self.nodes_log_dir, node_name + '.xml'), 'r') as node_file:
                node_config = node_file.read()
            self.create_node(node_name, node_config)
            return True
        except:
            return False
    
    def backup_all_nodes(self):
        """
        Backup all nodes
        """
        try:
            nodes = self.get_nodes()
            for node in nodes:
                if self.loggers:
                    self.backup_node_build_log(node_name)
                node_name = node['name']
                self.backup_node(node_name)
            return True
        except:
            return False
    
    def restore_all_nodes(self):
        """
        Restore all nodes
        """
        try:
            for node in os.listdir(self.nodes_dir):
                node_name = node.split('.')[0]
                if self.loggers:
                    self.restore_node_build_log(node_name)
                self.restore_node(node_name)
            
            return True
        except:
            return False
    
    def backup_all_nodes_exept(self, node_name):
        """
        Backup all nodes except node
        """
        try:
            nodes = self.get_nodes()
            for node in nodes:
                if node['name'] != node_name:
                    node_name = node['name']
                    self.backup_node(node_name)
            return True
        except:
            return False
    
    def restore_all_nodes_exept_node(self, node_name):
        """
        Restore all nodes except node
        """
        try:
            for node in os.listdir(self.nodes_dir):
                node_name = node.split('.')[0]
                if node_name != node_name:
                    if self.loggers:
                        self.restore_node_build_log(node_name)
                    self.restore_node(node_name)
            
            return True
        except:
            return False

    def restore_folder_build_log(self, folder_name,job_build_number=None):
        """
        Restore folder build log
        """
        try:
            for folder in os.listdir(self.folders_dir):
                if folder_name==folder:
                    for job in os.listdir(os.path.join(self.folders_dir,folder)):
                        if job_build_number==None:
                            job_build_number=get_job_build_number(job)
                        self.restore_log(job,job_build_number,file_path=os.path.join(self.folders_dir,folder))

            return True
        except:
            return False
    def backup_view(self, view_name):
        """
        Backup view
        """
        try:
            view_config = self.get_view_config(view_name)
            if view_config:
                if self.loggers==True:
                    self.backup_view_build_log(view_name)
                with open(os.path.join(self.views_dir, view_name + '.xml'), 'w') as view_file:
                    view_file.write(view_config)
                self.write_json_file("details.json","Views",view_name, (self.views_dir, view_name + '.xml'))
            return True
        except:
            return False
    
    def backup_folder(self, folder_name):
        """
        Backup folder
        """
        try:
            jobs = self.get_jobs_by_folder(folder_name)
            for job in jobs:
                if self.loggers==True:
                    self.backup_folder_build_log(folder_name)
                job_name = job['name']
                self.backup_job(job_name,file_path=self.folder_jobs_dir,folder_name=folder_name)
            return True
        except:
            return False
    
    def restore_folder(self, folder_name):
        """
        Restore folder
        """
        try:
            for folder in os.listdir(self.folders_dir):
                if folder_name==folder:
                    for job in os.listdir(os.path.join(self.folders_dir,folder)):
                        job_name = job.split('.')[0]
                        self.restore_job(job_name,file_path=os.path.join(self.folders_dir,folder),folder_name=folder_name)
            return True
        except:
            return False
    
    def backup_job(self, job_name, file_path=None,folder_name=None):
        """
        Backup job
        """
        try:
            job_config = self.get_job_config(job_name)
            
            if file_path==None and folder_name==None:
                with open(os.path.join(self.jobs_dir, job_name + '.xml'), 'w') as job_file:
                    job_file.write(job_config)
                self.write_json_file("details.json","Jobs",job_name, (self.jobs_dir, job_name + '.xml'))
                
            else:
                with open(os.path.join(file_path, job_name + '.xml'), 'w') as job_file:
                    job_file.write(job_config)
                self.write_json_file("details.json","Folder",folder_name,{job_name:(file_path, job_name + '.xml')})
                
            return True
        except:
            return False

    def restore_job(self, job_name, file_path=None,folder_name=None):
        """
        Restore job
        """
        try:
            if file_path==None:
                with open(os.path.join(self.jobs_dir, job_name + '.xml'), 'r') as job_file:
                    job_config = job_file.read()
                self.create_job(job_name)
            else:
                with open(os.path.join(file_path, job_name + '.xml'), 'r') as job_file:
                    job_config = job_file.read()
                self.create_folder_job(folder_name, job_name)
            return True
        except Exception as e:
            print(e)
            return False
    
    def backup_plugin(self, plugin_name):
        """
        Backup plugin
        """
        try:
            plugin_config = self.get_plugin_config(plugin_name)
            with open(os.path.join(self.plugins_dir, plugin_name + '.xml'), 'w') as plugin_file:
                plugin_file.write(plugin_config)
            self.write_json_file("details.json","Plugins",plugin_name, (self.plugins_dir, plugin_name + '.xml'))
            return True
        except:
            return False
    
    def backup_all_jobs(self):
        """
        Backup all jobs
        """
        try:
            jobs = self.get_jobs()
            for job in jobs:
                if self.loggers:
                    self.backup_log(job_name=job['name'])
                self.backup_job(job['name'])
            return True
        except Exception as e:
            print(e)
            return False
    
    def backup_all_folder(self):
        """
        Backup all folder
        """
        try:
            folders = self.get_folders()
            for folder in folders:
                if self.loggers:
                    self.backup_folder_build_log(folder_name=folder['name'])
                self.backup_folder(folder['name'])
            return True
        except:
            return False
    
    def restore_all_jobs_exept(self, job_name):
        """
        Restore all jobs except job
        """
        try:
            for job in os.listdir(self.jobs_dir):
                if job_name != job.split('.')[0]:
                    self.restore_job(job.split('.')[0])
                    self.restore_log(job.split('.')[0])
            return True
        except:
            return False
    def backup_all_jobs_except_job(self, job_name):
        """
        Backup all jobs except job
        """
        try:
            jobs = self.get_jobs()
            for job in jobs:
                if job['name'] != job_name:
                    if self.loggers:
                        self.backup_log(job_name=job['name'])
                    self.backup_job(job['name'])
            return True
        except:
            return False

    def backup_all_folder_except_folder(self, folder_name):
        """
        Backup all folder except folder
        """
        try:
            folders = self.get_folders()
            for folder in folders:
                if folder['name'] != folder_name:
                    if self.loggers==True:
                        self.backup_folder_build_log(folder_name=folder['name'])
                    self.backup_folder(folder['name'])
            return True
        except:
            return False
    
    def backup_all_plugin_except_plugin(self, plugin_name):
        """
        Backup plugin except plugin
        """
        try:
            plugins = self.get_plugins()
            for plugin in plugins:
                if plugin['shortName'] != plugin_name:
                    if self.loggers==True:
                        self.backup_plugin_build_log(plugin_name=plugin['shortName'])
                    self.backup_plugin(plugin['shortName'])
            return True
        except:
            return False
    
    def restore_all_jobs(self):
        """
        Restore all jobs in jobs directory
        """
        try:
            for job in os.listdir(self.jobs_dir):
                if job.endswith(".xml"):
                    self.restore_job(job[:-4])
            return True
        except Exception as e:
            print(e)
            return False
    
    def restore_all_folders(self):
        """
        Restore all folder
        """
        try:
            for foldername in os.listdir(self.folders_dir):
                    self.restore_folder(str(folder))
            return True
        except:
            return False

    def backup_all_plugins(self):
        """
        Backup all plugin
        """
        try:
            plugins = self.get_plugins()
            for plugin in plugins:
                self.backup_plugin(plugin['shortName'])
            return True
        except:
            return False

    def restore_all_plugin(self):
        """
        Restore all plugin
        """
        try:
            for plugin in os.listdir(self.plugins_dir):
                if plugin.endswith(".xml"):
                    if self.loggers==True:
                        self.restore_plugin_build_log(plugin_name=plugin[:-4])
                    self.restore_plugin(plugin[:-4])
            
            return True
        except:
            return False

    def restore_all_folders_except_folder(self, folder_name):
        """
        Restore all folders except folder
        """
        try:
            for folder in os.listdir(self.folders_dir):
                if folder != folder_name:
                    self.restore_folder(folder)
            
            return True
        except:
            return False

    def backup_all_views(self):
        """
        Backup all views
        """
        try:
            views = self.get_views()
            for view in views:
                self.backup_view(view['name'])
            return True
        except:
            return False

    def backup_all_views_except_view(self, view_name):
        """
        Backup all views except view
        """
        try:
            views = self.get_views()
            for view in views:
                if view['name'] != view_name:
                    self.backup_view(view['name'])
            return True
        except:
            return False

    def restore_view(self, view_name):
        """
        Restore view
        """
        try:
            with open(os.path.join(self.views_dir, view_name + '.xml'), 'r') as view_file:
                view_config = view_file.read()
            self.create_view(view_name, view_config)
            return True
        except:
            return False

    def restore_all_views(self):
        """
        Restore all views
        """
        try:
            for view in os.listdir(self.views_dir):
                if view.endswith(".xml"):
                    self.restore_view(view[:-4])
            
            return True
        except:
            return False

    def restore_all_views_except_view(self, view_name):
        """
        Restore all views except view
        """
        try:
            for view in os.listdir(self.views_dir):
                if view.endswith(".xml"):
                    if view[:-4] != view_name:
                        self.restore_view(view[:-4])
            
            return True
        except:
            return False

    def restore_plugin(self, plugin_name):
        """
        Restore plugin
        """
        try:
            with open(os.path.join(self.plugins_dir, plugin_name + '.xml'), 'r') as plugin_file:
                plugin_config = plugin_file.read()
            self.create_plugin(plugin_name, plugin_config)
            return True
        except:
            return False

    def restore_all_plugins_except_plugin(self, plugin_name):
        """
        Restore all plugins except plugin
        """
        try:
            for plugin in os.listdir(self.plugins_dir):
                if plugin.endswith(".xml"):
                    if plugin[:-4] != plugin_name:
                        self.restore_plugin(plugin[:-4])
            
            return True
        except:
            return False

    def backup_all_logs(self):
        """
        Backup all logs
        """
        try:
            logs = self.get_logs()
            for log in logs:
                self.backup_log(log['name'])
            return True
        except:
            return False

    def backup_all_jobs_exept(self, job_name):
        """
        Backup all jobs except job
        """
        try:
            jobs = self.get_jobs()
            for job in jobs:
                if job['name'] != job_name:
                    self.backup_job(job['name'])
            return True
        except:
            return False
    def backup_all_plugins_except_plugin(self, plugin_name):
        """
        Backup all plugins except plugin
        """
        try:
            plugins = self.get_plugins()
            for plugin in plugins:
                if plugin['shortName'] != plugin_name:
                    self.backup_plugin(plugin['shortName'])
            return True
        except:
            return False

    def restore_all_jobs_except_job(self, job_name):
        """
        Restore all jobs except job
        """
        try:
            for job in os.listdir(self.jobs_dir):
                if job.endswith(".xml"):
                    if job[:-4] != job_name:
                        self.restore_job(job[:-4])
            
            return True
        except Exception as e:
            print(e)
            return False

    def backup_all(self):
        """
        Backup all
        """
        try:
            self.backup_all_jobs()
            self.backup_all_folder()
            self.backup_all_plugins()
            self.backup_all_logs()
            self.backup_all_views()
            return True
        except:
            return False
    def restore_all_plugins(self):
        """
        Restore all plugins
        """
        try:
            for plugin in os.listdir(self.plugins_dir):
                if plugin.endswith(".xml"):
                    self.restore_plugin(plugin[:-4])
            
            return True
        except:
            return False

    def restore_all(self):
        """
        Restore all
        """
        try:
            self.restore_all_jobs()
            self.restore_all_folders()
            self.restore_all_plugins()
            self.restore_all_views()
            return True
        except:
            return False
if __name__ == '__main__':

    argparser = argparse.ArgumentParser(description='Jenkins backup and restore')
    argparser.add_argument('-b', '--backup', help='Backup Jenkins', action='store_true')
    argparser.add_argument('-r', '--restore', help='Restore Jenkins', action='store_true')
    argparser.add_argument('-j', '--job', help='select job', action='store_true')
    argparser.add_argument('-f', '--folder', help='select folder', action='store_true')
    argparser.add_argument('-p', '--plugin', help='select plugin', action='store_true')
    argparser.add_argument('-l', '--log', help='select Log', action='store_true')
    argparser.add_argument('-v', '--view', help='select View',  action='store_true')
    argparser.add_argument('-n', '--node', help='select node',  action='store_true')
    argparser.add_argument('-a', '--all', help='all', action='store_true')

    argparser.add_argument('-fj', '--filteredjob', help='filter by job name')
    argparser.add_argument('-ff', '--filteredfolder', help='filter by folder name')
    argparser.add_argument('-fp', '--filteredplugin', help='filter by plugin name')
    argparser.add_argument('-fv', '--filteredview', help='View name')
    argparser.add_argument('-fn', '--filterednode', help='filter node name')

    argparser.add_argument('-ej', '--alljobsexcept', help='all jobs except')
    argparser.add_argument('-ef', '--allfoldersexcept', help='Backup all folders except')
    argparser.add_argument('-ep', '--allpluginsexcept', help='Backup all plugins except')
    argparser.add_argument('-ev', '--allviewsexcept', help='Backup all views except')

    argparser.add_argument('-u', '--url', help='Jenkins URL')
    argparser.add_argument('-un', '--username', help='Jenkins username')
    argparser.add_argument('-t', '--token', help='Jenkins token')

    argparser.add_argument('-bd', '--backup_dir', help='Backup directory')
    argparser.add_argument('-rd', '--restore_dir', help='Restore directory')
    argparser.add_argument('-zd', '--zip_dir', help='Zip directory')
    argparser.add_argument('-z', '--zip', help='Zip file')

    args = argparser.parse_args()
    print('Backup Jenkins',args.all)
    myJenkins=MyJenkins(args)
    print(myJenkins.backup_all_jobs())
    if args.backup:
        myJenkins.create_backup_dir()
        try:
            if args.all:
                counter = 0
                if args.folder==True:
                    counter+=1
                    myJenkins.backup_all_folder()
                if args.view==True:
                    counter+=1
                    myJenkins.backup_all_views()
                if args.job == True:
                    counter+=1
                    myJenkins.backup_all_jobs()
                if args.plugin==True:
                    counter+=1
                    myJenkins.backup_all_plugins()
                if args.log==True:
                    counter+=1
                    myJenkins.backup_all_logs()
                
                if counter == 0:
                    myJenkins.backup_all()
            elif args.filteredjob:
                myJenkins.backup_job(args.filteredjob)
            elif args.filteredfolder:
                myJenkins.backup_folder(args.filteredfolder)
            elif args.filteredplugin:
                myJenkins.backup_plugin(args.filteredplugin)
            elif args.filteredview:
                myJenkins.backup_view(args.filteredview) 
            elif args.filterednode:
                myJenkins.backup_node(args.filterednode)     
            elif args.alljobsexcept: 
                myJenkins.backup_all_jobs_except_job(args.alljobsexcept)  
            elif args.allfoldersexcept:
                myJenkins.backup_all_folder_except_folder(args.allfoldersexcept)
            elif args.allpluginsexcept:
                myJenkins.backup_all_plugins_except_plugin(args.allpluginsexcept)
            elif args.allviewsexcept:
                myJenkins.backup_all_views_except_view(args.allviewsexcept)
            
            else:
                print('Please select what to backup')
        except:
            pass
        finally:
            # if args.zip_dir is None:
            #     myJenkins.zip_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'zip')
            # else:
            #     myJenkins.zip_dir = args.zip_dir
            # if args.zip is None:
            #     myJenkins.zip_file = os.path.join(myJenkins.zip_dir, 'backup.zip') 
            # else:
            #     myJenkins.zip_file = os.path.join(self.zip_dir, args.zip)
            myJenkins.compress_all_files_in_dir(myJenkins.zip_file,myJenkins.backup_dir)
            myJenkins.remove_all_files_in_dir(myJenkins.backup_dir)
    elif args.restore:
        if args.restore_dir is None:
            myJenkins.decompress_all_files_in_dir(myJenkins.zip_file,myJenkins.restore_dir)
        if args.all:
            counter = 0
            if args.folder:
                counter+=1
                myJenkins.restore_all_folders()
            if args.view:
                counter+=1
                myJenkins.restore_all_views()
            if args.job:
                counter+=1
                myJenkins.restore_all_jobs()
            if args.plugin:
                counter+=1
                myJenkins.restore_all_plugins()
            
            if counter == 0:
                myJenkins.restore_all()
        elif args.filteredjob:
            myJenkins.restore_job(args.filteredjob)
        elif args.filteredfolder:
            myJenkins.restore_folder(args.filteredfolder)
        elif args.plugin:
            myJenkins.restore_plugin(args.filteredplugin)
        elif args.filteredview:
            myJenkins.restore_view(args.filteredview)
        elif args.filterednode:
            myJenkins.restore_node(args.filterednode)    
        elif args.alljobsexcept:
            myJenkins.restore_all_jobs_except_job(args.alljobsexcept)
        elif args.allfoldersexcept:
            myJenkins.restore_all_folders_except_folder(args.allfoldersexcept)
        elif args.allpluginsexcept:
            myJenkins.restore_all_plugins_except_plugin(args.allpluginsexcept)
        elif args.allviewsexcept:
            myJenkins.restore_all_views_except_view(args.allviewsexcept)
        
        else:
            print('Please select what to restore')
            
            

    # usage
    # python jenkins_backup_restore.py -a -r -u http://localhost:8080 -un jenkins_username -t Api_token -bd backup_directory -rd restore_dirctory -zd zip_directory -z zip_file
    # python jenkins_backup_restore.py -a -b -u http://localhost:8080 -un jenkins_username -t Api_token -bd backup_directory -rd restore_dirctory -zd zip_directory -z zip_file
    # python jenkins_backup_restore.py -j job_name http://localhost:8080 -un jenkins_username -t Api_token
    # python jenkins_backup_restore.py -f folder_name http://localhost:8080 -un jenkins_username -t Api_token
    # python jenkins_backup_restore.py -p plugin_name http://localhost:8080 -un jenkins_username -t Api_token
    # python jenkins_backup_restore.py -l -j job_name  http://localhost:8080 -un jenkins_username -t Api_token