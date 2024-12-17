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
  default = "ami-00bdd1309f093baa7"
}

variable "key_name" {
  type    = string
  default = "junho_us"
}

variable "user" {
  type    = string
  default = "ubuntu"
}