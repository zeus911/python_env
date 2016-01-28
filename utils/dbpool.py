#!/usr/bin/env python
#-*- encoding:utf-8 -*-

'''
使用DBUtils来实现数据库线程池
'''

import MySQLdb
from DBUtils.PooledDB import PooledDB
from MySQLdb.cursors import DictCursor
import ConfigParser
cf = ConfigParser.ConfigParser()
cf.read('../conf/app.conf')

import lggr
mylggr = lggr.Lggr()
mylggr.add(lggr.ALL, lggr.FilePrinter(cf.get('db','error_log')))

class DB(object):
    '''
        MySQLdb 连接池
    '''
    _pool = None

    def __init__(self):
        self._conn = DB._getConn()
        self._cursor = self._conn.cursor()

    @staticmethod
    def _getConn():
        if DB._pool is None:
            try:
                DB._pool = PooledDB(
                    MySQLdb,
                    mincached=cf.get('db','mincached'),
                    maxcached=cf.get('db','maxcached'),
                    maxusage=cf.get('db','maxusage'),
                    host=cf.get('db','host'),
                    port=cf.get('db','port'),
                    user=cf.get('db','user'),
                    passwd=cf.get('db','passwd'),
                    db=cf.get('db','db'),
                    cursorclass=DictCursor
                )
            except Exception as e:
                print 'dbpoll error:',e
        return DB._pool.connection()

    def _query(self, sql, param):
        '''
        sql请求
        :param sql: sql语句
        :param param: 参数
        :return: 返回查询数量，错误返回False
        '''
        try:
            if param is None:
                count = self._cursor.execute(sql)
            else:
                count = self._cursor.execute(sql, param)
        except Exception as e:
            mylggr.error(sql + '\n' + str(e))
            return False
        return count

    def queryAll(self, sql, param=None):
        '''
        查询并返回所有数据
        :param sql: sql select语句
        :param param: 参数
        :return: 返回请求结果，错误返回False
        '''
        count = self._query(sql, param)
        if count == False or count < 0:
            return False
        elif count > 0:
            try:
                result = self._cursor.fetchall()
            except Exception as e:
                mylggr.error(sql + '\n' + str(e))
                result = False
        return result

    def queryOne(self, sql, param=None):
        '''
        查询并返回一条数据
        :param sql: sql select语句
        :param param: 参数
        :return: 返回请求结果，错误返回False
        '''
        count = self._query(sql, param)
        if count == False or count < 0:
            return False
        elif count > 0:
            try:
                result = self._cursor.fethone()
            except Exception as e:
                mylggr.error(sql + '\n' + str(e))
                result = False
        return result

    def queryMany(self, sql, num, param=None):
        '''
        查询并返回num个数据
        :param sql: sql select语句
        :param num: 请求数量
        :param param: 参数
        :return: 返回请求结果
        '''
        count = self._query(sql, param)
        if count == False or count < 0:
            return False
        elif count > 0:
            try:
                result = self._cursor.fetchmany(num)
            except Exception as e:
                mylggr.error(sql + '\n' + str(e))
                result = False
        return result

    def _getInsertId(self):
        '''
        :return: 获取当前连接最后一次插入操作生成的id,如果没有则为０
        '''
        try:
            self._cursor.execute('select LAST_INSERT_ID() last_id;')
            result = self._cursor.fetchall()
        except Exception as e:
            mylggr.error(sql + '\n' + str(e))
            return False
        return result[0]['last_id']

    def insertOne(self, sql, values,autocommit=True):
        '''
        插入一条数据
        :sql: sql insert语句
        :param values: 插入数据
        ;autocommit : 是否自动提交
        :return: 返回id
        '''
        try:
            self._cursor.execute(sql, values)
            if autocommit:
                self.commit()
        except Exception as e:
            mylggr.error(sql + '\n' + str(e))
            return False
        return self._getInsertId()

    def insertMany(self, sql, values,autocommit=True):
        '''
        插入多个数据
        :param sql: sql insert语句
        :param values: 插入数据
        ;autocommit : 是否自动提交
        :return: 返回插入数据数量
        '''
        try:
            count = self._cursor.executemany(sql,values)
            if autocommit:
                self.commit()
        except Exception as e:
            mylggr.error(sql + '\n' + str(e))
            return  False
        return count

    def update(self, sql, param=None,autocommit=True):
        '''
        更新数据
        :param sql: sql update语句
        :param param: 参数
        ;autocommit : 是否自动提交
        :return: 返回更新数量
        '''
        try:
            count = self._query(sql, param)
            if autocommit:
                self.commit()
        except Exception as e:
            mylggr.error(sql + '\n' + str(e))
            return False
        return count

    def delete(self, sql, param=None,autocommit=True):
        '''
        删除数据
        :param sql: sql delete语句
        :param param: 参数
        ;autocommit : 是否自动提交
        :return: 返回删除数量
        '''
        try:
            count = self._query(sql, param)
            if autocommit:
                self.commit()
        except Exception as e:
            mylggr.error(sql + '\n' + str(e))
            return False
        return count

    def commit(self):
        '''
        提交事务
        :return: 成功返回True,否则返回False
        '''
        try:
            self._conn.commit()
        except Exception as e:
            mylggr.error(str(e))
            return False
        return True

    def rollback(self):
        '''
        回滚事务
        :return: 成功返回True,否则返回False
        '''
        try:
            self._conn.rollback()
        except Exception as e:
            mylggr.error(str(e))
            return False
        return True

    def close(self):
        '''
        关闭连接
        :return: 成功返回True,否则返回False
        '''
        try:
            self._cursor.close()
            self._conn.close()
        except Exception as e:
            mylggr.error(str(e))
            return False
        return True

if __name__ == '__main__':
    db = DB()
    #print db.insertOne('insert test (id) values (%s)', 3)
    #print db.insertOne('insert test (id) values (%s)', 4)
    #print db.queryAll('select * from test')
    #print db.update('update test set id=5 where id=1')
    #print db.queryAll('select * from test')
    #db.rollback()
