variable "ami_id" {
  type = string
}

variable "key_name" {
  type = string
}

variable "availability_zone" {
  type = string
}

variable "instance_group" {
  type = list
}

variable "public_subnet_id" {
  type = string
}

variable "security_group_id" {
  type = string
}

variable "user" {
  type = string
}

variable "resource_prefix" {
  type = string
}

variable "ec2_instance_profile" {
  type = string
}