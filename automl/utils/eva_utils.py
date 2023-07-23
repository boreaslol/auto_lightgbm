# -*- coding: utf-8 -*-
"""
Created on Wed Aug 12 21:41:55 2020

@author: meizihang
"""

# -*- coding: utf-8 -*-

# 模型评价
from sklearn.metrics import accuracy_score, recall_score, precision_score, confusion_matrix, classification_report, \
    cohen_kappa_score, f1_score, fbeta_score
import sklearn.metrics as metrics
import math
import toad
import numpy as np
from toad.stats import *

# 调用solveIV函数，计算IV（dataframe）
def solveIV(dev_data, var_names, dep, iv_only=True,cpu_cores=1):
    # TODO toad.quality涉及到多进程，需要指定/重写
    IV = toad.quality(dev_data[var_names + [dep]], target=dep, iv_only=iv_only,cpu_cores=cpu_cores)
    combiner = toad.transform.Combiner()
    combiner.fit(dev_data[var_names + [dep]], dev_data[dep], method='chi', min_samples=0.05)
    dev_data_bin = combiner.transform(dev_data[var_names + [dep]])
    WOETransformer = toad.transform.WOETransformer()
    dev_data_woe = WOETransformer.fit_transform(dev_data_bin[var_names + [dep]], dev_data_bin[dep])
    lis = []
    for i in IV.index:
        woe_set = set(dev_data_woe[i].map(lambda x: float(x)))
        woe_lis = list(map(abs, woe_set))
        lis.append(np.sum(woe_lis))
    IV['策略度'] = lis
    return IV


# 计算dev和off上的KS值
def sloveKS(model, X, Y):
    Y_predict = model.predict(X)
    nrows = X.shape[0]
    lis = [(Y_predict[i], Y.values[i], 1) for i in range(nrows)]
    ks_lis = sorted(lis, key=lambda x: x[0], reverse=True)
    KS = list()
    bad = sum([w for (p, y, w) in ks_lis if y > 0.5])
    good = sum([w for (p, y, w) in ks_lis if y <= 0.5])
    bad_cnt, good_cnt = 0, 0
    for (p, y, w) in ks_lis:
        if y > 0.5:
            bad_cnt += w
        else:
            good_cnt += w
        ks = math.fabs((bad_cnt / bad) - (good_cnt / good))
        KS.append(ks)
    return max(KS)


# 计算off相对于dev的PSI
def slovePSI(model, dev_x, val_x):
    dev_predict_y = model.predict(dev_x)
    dev_nrows = dev_x.shape[0]
    dev_predict_y.sort()
    cutpoint = [-100] + [dev_predict_y[int(dev_nrows / 10 * i)] for i in range(1, 10)] + [100]
    cutpoint = list(set(cutpoint))
    val_predict_y = model.predict(val_x)
    val_nrows = val_x.shape[0]
    PSI = 0
    for i in range(len(cutpoint) - 1):
        start_point, end_point = cutpoint[i], cutpoint[i + 1]
        dev_cnt = [p for p in dev_predict_y if start_point <= p < end_point]
        dev_ratio = len(dev_cnt) / dev_nrows + 1e-10
        val_cnt = [p for p in val_predict_y if start_point <= p < end_point]
        val_ratio = len(val_cnt) / val_nrows + 1e-10
        psi = (dev_ratio - val_ratio) * math.log(dev_ratio / val_ratio)
        PSI += psi
    return PSI
def confusion_matrix(y, pred):
    # 产生混淆矩阵的四个指标
    tn, fp, fn, tp = metrics.confusion_matrix(y, pred).ravel()

    # 产生衍生指标
    fpr = fp / (fp + tn)  # 假真率／特异度
    tpr = tp / (tp + fn)  # 灵敏度／召回率
    depth = (tp + fp) / (tn + fp + fn + tp)  # Rate of positive predictions.
    ppv = tp / (tp + fp)  # 精准率
    lift = ppv / ((tp + fn) / (tn + fp + fn + tp))  # 提升度
    afdr = fp / tp  # (虚报／命中)／好账户误判率
    return lift


# 单类计算各种评价指标
def normall_evl(valid_y, y_pred):
    dct = {}
    dct['分类准确率为'] = accuracy_score(valid_y, y_pred)
    dct['宏平均准确率'] = precision_score(valid_y, y_pred, average='macro')
    dct['微平均准确率'] = precision_score(valid_y, y_pred, average='micro')

    dct['宏平均召回率为'] = recall_score(valid_y, y_pred, average='macro')
    dct['微平均召回率为'] = recall_score(valid_y, y_pred, average='micro')

    dct['宏平均f1值为'] = f1_score(valid_y, y_pred, average='macro')
    dct['微平均f1值为'] = f1_score(valid_y, y_pred, average='micro')
    dct['lift值为'] = confusion_matrix(valid_y, y_pred)
    return dct


# 多类分别计算评价指标
def evl_all(df, dep, pred_class):
    for i in set(df[pred_class]):
        y_label = df[dep]
        print(i, normall_evl(y_label, pred_class))