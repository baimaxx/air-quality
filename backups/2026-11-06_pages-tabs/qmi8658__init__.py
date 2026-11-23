import esphome.codegen as cg
from esphome.components import i2c
from esphome.components.motion import MotionComponent

CODEOWNERS = ["@clydebarrow"]
# 注意：上游误把平台组件 "motion" 写进 DEPENDENCIES，导致配置校验必然失败
# （motion 没有顶层配置项，无法出现在 config 里）。此处移除，与 bmi270/lsm6ds 保持一致。
DEPENDENCIES = ["i2c"]

CONF_QMI8658_ID = "qmi8658_id"
#  C++ namespace / class
qmi8658_ns = cg.esphome_ns.namespace("qmi8658")
QMI8658Component = qmi8658_ns.class_("QMI8658Component", MotionComponent, i2c.I2CDevice)

CONFIG_SCHEMA = {}
