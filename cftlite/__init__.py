try:
	import pymysql

	pymysql.install_as_MySQLdb()
except Exception:
	# If PyMySQL isn't installed, we'll rely on mysqlclient or sqlite.
	pass

