# Prime Reserve Bank - PyMySQL bridge for MySQL connectivity
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
