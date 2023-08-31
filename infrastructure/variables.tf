variable "region" {
  type    = string
  default = "us-west-2"
}

variable "resource_prefix" {
  type    = string
  default = "collect_cpuid"
}

variable "availability_zone" {
  type    = string
  default = "us-west-2c"
}

variable "ami_id" {
  type    = string
  default = "ami-04d814e732870ab10"
}

variable "key_name" {
  type    = string
  default = "junho_us"
}

variable "user" {
  type    = string
  default = "ubuntu"
}