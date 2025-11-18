INFO:     Will watch for changes in these directories: ['C:\\Users\\L073881\\OneDrive - Eli Lilly and Company\\Documents\\OLD_VDI\\Documents\\VS Code\\verso_ai\\verso_ai_prod']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [16408] using WatchFiles
Process SpawnProcess-1:
Traceback (most recent call last):
  File "C:\Users\L073881\AppData\Local\Programs\Python\Python313\Lib\multiprocessing\process.py", line 313, in _bootstrap
    self.run()
    ~~~~~~~~^^
  File "C:\Users\L073881\AppData\Local\Programs\Python\Python313\Lib\multiprocessing\process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\uvicorn\_subprocess.py", line 80, in subprocess_started
    target(sockets=sockets)
    ~~~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\uvicorn\server.py", line 67, in run      
    return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
  File "C:\Users\L073881\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Users\L073881\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Users\L073881\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\uvicorn\server.py", line 71, in serve    
    await self._serve(sockets)
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\uvicorn\server.py", line 78, in _serve   
    config.load()
    ~~~~~~~~~~~^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\uvicorn\config.py", line 438, in load    
    self.loaded_app = import_from_string(self.app)
                      ~~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\uvicorn\importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "C:\Users\L073881\AppData\Local\Programs\Python\Python313\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 1026, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\verso_ai_prod\app.py", line 38, in <module>
    gh = GitHubRepo(token=GITHUB_TOKEN, repo_full_name=GITHUB_REPO)
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\verso_ai_prod\git_utils.py", line 9, in __init__
    self.repo = self.gh.get_repo(repo_full_name)
                ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\github\MainClass.py", line 479, in get_repo
    headers, data = self.__requester.requestJsonAndCheck("GET", url)
                    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\github\Requester.py", line 623, in requestJsonAndCheck
    return self.__check(
           ~~~~~~~~~~~~^
        *self.requestJson(
        ^^^^^^^^^^^^^^^^^^
    ...<7 lines>...
        )
        ^
    )
    ^
  File "C:\Users\L073881\OneDrive - Eli Lilly and Company\Documents\OLD_VDI\Documents\VS Code\verso_ai\env\Lib\site-packages\github\Requester.py", line 853, in __check
    raise self.createException(status, responseHeaders, data)
github.GithubException.UnknownObjectException: 404 {"message": "Not Found", "documentation_url": "https://docs.github.com/rest", "status": "404"}
