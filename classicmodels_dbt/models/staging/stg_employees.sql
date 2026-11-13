select
    employeeNumber as employee_id,
    lastName       as last_name,
    firstName      as first_name,
    extension      as extension,
    email          as email,
    officeCode     as office_code,
    reportsTo      as reports_to_employee_id,
    jobTitle       as job_title
from {{ source('classicmodels', 'employees') }}
