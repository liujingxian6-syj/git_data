#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sklearn.cluster import DBSCAN
from sklearn import metrics
import seaborn as sns

class model_DBScan():
    def __init__(self,OutRule,power=2):
        self.power = power
        self.data = OutRule
        
    def DBScan_run(self):
        #训练DBScan聚类模型
        power  = self.power
        df_db = self.data
        
        if np.abs(df_db.loc[:,'y']).mean() < 1:
            df_db.loc[:,'y1'] = df_db['y']*100
            df_db.loc[:,'δ^2'] = np.power((df_db['y']-df_db['yhat']*100),power)
        else:
            df_db.loc[:,'y1'] = df_db['y']
            df_db.loc[:,'δ^2'] = np.power(df_db['y']-df_db['yhat'],power)

        # 设置半径为δ^2的95%分位数，最小样本量为10，建模，可补充优化寻参过程
        X = df_db[['y1','δ^2']]
        arg_eps = np.abs(np.percentile(X['δ^2'],95))
        db = DBSCAN(eps=arg_eps, min_samples=10).fit(X)

        labels = db.labels_
        df_db['cluster_db'] = db.labels_   # 在数据集最后一列加上经过DBSCAN聚类后的结果

        df_db['outlier_pred'] = 0
        df_db.loc[df_db['cluster_db']==-1,'outlier_pred'] = 1
        
        """
        聚类效果可视化
        """
        '''
        raito = df_db.loc[df_db['cluster_db']==-1].ds.count()/df_db.ds.count() #labels=-1的个数除以总数，计算噪声点个数占总数的比例
        print('噪声比:', format(raito, '.2%'))
        n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0) # 获取分簇的数目
        print('分簇的数目: %d' % n_clusters_)
        print("轮廓系数: %0.3f" % metrics.silhouette_score(X, df_db['cluster_db'])) #轮廓系数评价聚类的好坏
        sns.relplot(x='y1',y='δ^2', hue="cluster_db",style="cluster_db",data=df_db)
        '''
        del df_db['cluster_db']
        df_db = df_db.iloc[-1:].reset_index(drop=True)  #仅保存最后一条记录
        return df_db